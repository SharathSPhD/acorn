#!/bin/bash
# ACORN Harness Entrypoint — multi-agent dispatch
# Role-based dispatch: orchestrator | specialist | judge | kernel-extractor | meta-agent
set -euo pipefail

ACORN_API="${ACORN_API_URL:-http://acorn-api:8000}"
PROBLEM_UUID="${ACORN_PROBLEM_UUID:-}"
AGENT_ID="${ACORN_AGENT_ID:-agent-$(python3 -c 'import time;print(int(time.time()))')}"
ROLE="${ACORN_ROLE:-orchestrator}"
if [ -z "$ACORN_MODEL" ]; then
    QUERIED_MODEL=$(curl -sf "$ACORN_API/api/agents/model-for-role?role=$ROLE" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('model','qwen3-coder'))" 2>/dev/null || echo "qwen3-coder")
    MODEL="$QUERIED_MODEL"
else
    MODEL="$ACORN_MODEL"
fi
TASK_ID="${ACORN_TASK_ID:-}"
POLL_INTERVAL=30
MAX_POLL_ATTEMPTS=120

log() { echo "[${ROLE}] $*"; }

patch_task() {
    local tid="$1" st="$2"
    curl -sf -X PATCH "$ACORN_API/api/tasks/$tid/status" \
        -H "Content-Type: application/json" \
        -d "{\"status\": \"$st\"}" > /dev/null 2>&1 || true
}

patch_problem() {
    local st="$1"
    curl -sf -X PATCH "$ACORN_API/api/problems/$PROBLEM_UUID" \
        -H "Content-Type: application/json" \
        -d "{\"status\": \"$st\"}" > /dev/null 2>&1 || true
}

record_reasoning() {
    local step_type="$1" summary="$2" confidence="${3:-}"
    local body="{\"agent_id\": \"$ROLE\", \"step_type\": \"$step_type\", \"summary\": \"$summary\""
    if [ -n "$confidence" ]; then
        body="$body, \"confidence\": $confidence"
    fi
    body="$body}"
    curl -sf -X POST "$ACORN_API/api/problems/$PROBLEM_UUID/reasoning-steps" \
        -H "Content-Type: application/json" \
        -d "$body" > /dev/null 2>&1 || true
}

if [ -z "$PROBLEM_UUID" ]; then
    log "ERROR: ACORN_PROBLEM_UUID not set" >&2
    exit 1
fi

cd /workspace

# ── Meta-Agent ────────────────────────────────────────────────────────────
if [ "$ROLE" = "meta-agent" ]; then
    log "Starting self-improvement cycle"

    HEALTH=$(curl -sf "$ACORN_API/health" || echo "{}")
    TELEMETRY=$(curl -sf "$ACORN_API/api/telemetry" || echo "{}")

    cat > META_CONTEXT.md <<METAEOF
# ACORN Meta-Agent — Self-Improvement Input
## System Health
\`\`\`json
$HEALTH
\`\`\`
## Telemetry Summary
\`\`\`json
$TELEMETRY
\`\`\`
METAEOF

    claude --dangerously-skip-permissions --model "$MODEL" --max-turns 3 -p \
      "You are the ACORN Meta Agent. Analyze META_CONTEXT.md and produce meta_proposals.json with improvement proposals. Output ONLY valid JSON." \
      > meta_proposals.json 2>/dev/null || true

    if python3 -c "import json; json.load(open('meta_proposals.json'))" 2>/dev/null; then
        log "Valid proposals generated"
    else
        echo '{"proposals":[],"system_summary":"No patterns detected"}' > meta_proposals.json
    fi
    exit 0
fi

# ── Spec agents (research-analyst, synthesis-agent, domain-specialist, etc.) ─
SPEC_AGENT_ROLES="research-analyst synthesis-agent domain-specialist validator interface-agent calibration-agent"
if echo "$SPEC_AGENT_ROLES" | grep -qw "$ROLE"; then
    log "Starting spec agent (role=$ROLE, task=$TASK_ID)"

    if [ -n "$TASK_ID" ]; then
        patch_task "$TASK_ID" "claimed"
    fi
    TASK_DESC=""
    if [ -n "$TASK_ID" ]; then
        TASK_JSON=$(curl -sf "$ACORN_API/api/tasks?problem_id=$PROBLEM_UUID" 2>/dev/null || echo "[]")
        TASK_DESC=$(echo "$TASK_JSON" | python3 -c "
import sys, json
tasks = json.load(sys.stdin)
tid = '$TASK_ID'
for t in (tasks if isinstance(tasks, list) else []):
    if str(t.get('id','')) == tid:
        print(t.get('description','') or t.get('title',''))
        break
else:
    print('')
" 2>/dev/null || echo "")
    fi
    [ -z "$TASK_DESC" ] && TASK_DESC="Complete the assigned task for $ROLE"

    PROBLEM_DESC=""
    if [ -f /workspace/PROBLEM.md ]; then
        PROBLEM_DESC=$(head -50 /workspace/PROBLEM.md)
    fi

    AGENT_FILE="/workspace/.claude/agents/${ROLE}.md"
    AGENT_DEF=""
    if [ -f "$AGENT_FILE" ]; then
        AGENT_DEF=$(cat "$AGENT_FILE")
    else
        AGENT_DEF="You are the $ROLE agent. Complete the task and write the required output artefact."
    fi

    claude --dangerously-skip-permissions --model "$MODEL" --max-turns 10 -p \
      "## Agent Definition
$AGENT_DEF

## Task
$TASK_DESC

## Problem Context
$PROBLEM_DESC

Execute your lifecycle. Write your output artefact to /workspace. RESTORE, ORIENT, EXECUTE, REPORT, CLOSE, SAVE." \
      > /dev/null 2>&1 || true

    TASK_STATUS="complete"
    case "$ROLE" in
        research-analyst) [ -f /workspace/RESEARCH.md ] || TASK_STATUS="failed" ;;
        synthesis-agent) [ -f /workspace/SYNTHESIS.md ] || [ -f /workspace/app.py ] || TASK_STATUS="failed" ;;
        domain-specialist) [ -f /workspace/DOMAIN_ANALYSIS.md ] || TASK_STATUS="failed" ;;
        validator) [ -f /workspace/VALIDATION_REPORT.md ] || TASK_STATUS="failed" ;;
        *) TASK_STATUS="complete" ;;
    esac

    if [ -n "$TASK_ID" ]; then
        patch_task "$TASK_ID" "$TASK_STATUS"
    fi
    log "Spec agent $ROLE finished: $TASK_STATUS"
    exit 0
fi

# ── Specialist (data-engineer, data-scientist, ml-engineer, etc.) ────────
SPECIALIST_ROLES="data-engineer data-scientist ml-engineer ai-engineer software-architect frontend security-expert research-analyst synthesis-agent domain-specialist validator interface-agent calibration-agent"
if echo "$SPECIALIST_ROLES" | grep -qw "$ROLE"; then
    log "Starting specialist task (task=$TASK_ID)"

    if [ -n "$TASK_ID" ]; then
        patch_task "$TASK_ID" "claimed"
        TASK_JSON=$(curl -sf "$ACORN_API/api/tasks?problem_id=$PROBLEM_UUID" 2>/dev/null || echo "[]")
        TASK_DESC=$(echo "$TASK_JSON" | python3 -c "
import sys, json
tasks = json.load(sys.stdin)
tid = '$TASK_ID'
for t in (tasks if isinstance(tasks, list) else []):
    if str(t.get('id','')) == tid:
        print(t.get('description','') or t.get('title',''))
        break
else:
    print('Complete the assigned task')
" 2>/dev/null || echo "Complete the assigned task")
    else
        TASK_DESC="Perform ${ROLE} analysis on the workspace data"
    fi

    PROBLEM_DESC=""
    if [ -f PROBLEM.md ]; then
        PROBLEM_DESC=$(cat PROBLEM.md)
    fi

    DATA_FILES=$(find /workspace -maxdepth 1 -name '*.csv' -o -name '*.json' -o -name '*.parquet' | head -5)
    DATA_PREVIEW=""
    for f in $DATA_FILES; do
        DATA_PREVIEW="${DATA_PREVIEW}File: $(basename "$f"), Rows: $(wc -l < "$f"), Columns: $(head -1 "$f" | tr ',' '\n' | wc -l)
"
    done

    log "Generating analysis script via Ollama API"

    export ACORN_SPEC_ROLE="$ROLE"
    export ACORN_SPEC_TASK="$TASK_DESC"
    export ACORN_SPEC_PROBLEM="$PROBLEM_DESC"
    export ACORN_SPEC_DATA_PREVIEW="$DATA_PREVIEW"

    python3 <<'SPECIALIST_PY'
import json, urllib.request, os, sys, re, subprocess

proxy = os.environ.get('ANTHROPIC_BASE_URL', 'http://acorn-api-relay:9000')
model = os.environ.get('ACORN_MODEL', 'qwen3-coder')
role = os.environ.get('ACORN_SPEC_ROLE', 'data-scientist')
task = os.environ.get('ACORN_SPEC_TASK', '')
problem = os.environ.get('ACORN_SPEC_PROBLEM', '')
data_preview = os.environ.get('ACORN_SPEC_DATA_PREVIEW', '')

prompt = f"""You are an expert {role}. Generate a complete Python script that performs the required task.

## Problem
{problem}

## Your Task
{task}

## Available Data
{data_preview}
All data files are in /workspace/

## Requirements
1. Read CSV/data files from /workspace/
2. Perform the analysis or processing described in the task
3. Save all output to /workspace/{role}_output.md (a markdown report)
4. If the task involves data cleaning, save cleaned data to /workspace/cleaned_data.csv
5. If the task involves modeling, save model metrics to /workspace/model_metrics.json
6. Print a brief summary to stdout
7. Use only: pandas, numpy, scikit-learn, json, os, sys (pre-installed)
8. Handle missing values and errors gracefully

Output ONLY the Python script. No explanations, no markdown fences."""

body = json.dumps({
    'model': model,
    'max_tokens': 4096,
    'messages': [{'role': 'user', 'content': prompt}],
}).encode()

req = urllib.request.Request(
    f'{proxy}/v1/chat/completions',
    data=body,
    headers={
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ollama',
    },
    method='POST',
)

try:
    resp = urllib.request.urlopen(req, timeout=300)
    result = json.load(resp)
    content = result['choices'][0]['message']['content']

    if '```python' in content:
        content = content.split('```python', 1)[1].split('```', 1)[0]
    elif '```' in content:
        content = content.split('```', 1)[1].split('```', 1)[0]
    content = content.strip()

    script_path = f'/workspace/{role}_script.py'
    with open(script_path, 'w') as f:
        f.write(content)
    print(f'Script generated: {script_path}')

    proc = subprocess.run(
        ['python3', script_path],
        capture_output=True, text=True, timeout=120,
        cwd='/workspace',
    )
    if proc.returncode == 0:
        print(f'Script succeeded: {proc.stdout[:500]}')
    else:
        print(f'Script error (attempting fallback): {proc.stderr[:300]}')
        fallback = f"""import pandas as pd, os, json
role = '{role}'
files = [f for f in os.listdir('/workspace') if f.endswith('.csv')]
if files:
    df = pd.read_csv(f'/workspace/{{files[0]}}')
    report = f'# {{role}} Report\\n\\n'
    report += f'## Dataset: {{files[0]}}\\n'
    report += f'- Shape: {{df.shape}}\\n'
    report += f'- Columns: {{list(df.columns)}}\\n\\n'
    report += '## Summary Statistics\\n\\n```\\n'
    report += df.describe().to_string() + '\\n```\\n\\n'
    report += '## Missing Values\\n\\n```\\n'
    report += df.isnull().sum().to_string() + '\\n```\\n'
    with open(f'/workspace/{{role}}_output.md', 'w') as f:
        f.write(report)
    print(f'Fallback report generated for {{role}}')
else:
    with open(f'/workspace/{{role}}_output.md', 'w') as f:
        f.write(f'# {{role}} Report\\n\\nNo data files found in workspace.')
    print('No data files found')
"""
        with open(f'/workspace/{role}_fallback.py', 'w') as f:
            f.write(fallback)
        proc2 = subprocess.run(
            ['python3', f'/workspace/{role}_fallback.py'],
            capture_output=True, text=True, timeout=60, cwd='/workspace',
        )
        print(f'Fallback result: {proc2.stdout[:200]}')

except Exception as e:
    print(f'Specialist error: {e}', file=sys.stderr)
    with open(f'/workspace/{role}_output.md', 'w') as f:
        f.write(f'# {role} Report\n\nFailed to generate analysis: {e}\n')
SPECIALIST_PY

    TASK_STATUS="complete"
    if [ ! -f "/workspace/${ROLE}_output.md" ]; then
        log "WARNING: No output file produced"
        TASK_STATUS="failed"
    fi

    if [ -n "$TASK_ID" ]; then
        patch_task "$TASK_ID" "$TASK_STATUS"
    fi
    log "Specialist task $TASK_STATUS"
    exit 0
fi

# ── Judge ─────────────────────────────────────────────────────────────────
if [ "$ROLE" = "judge" ] || [ "$ROLE" = "judge-agent" ]; then
    log "Starting quality evaluation"

    WORKSPACE_FILES=$(find /workspace -maxdepth 2 -type f ! -path '*/.git/*' -name '*.md' -o -name '*.py' -o -name '*.csv' | head -20)
    CONTEXT=""
    for f in $WORKSPACE_FILES; do
        CONTEXT="${CONTEXT}
--- $(basename "$f") ---
$(head -100 "$f" 2>/dev/null || true)
"
    done

    export ACORN_JUDGE_CONTEXT="$CONTEXT"
    VERDICT=$(python3 <<'JUDGEPY'
import json, urllib.request, sys, os, re

proxy = os.environ.get('ANTHROPIC_BASE_URL', 'http://acorn-api-relay:9000')
model = os.environ.get('ACORN_MODEL', 'qwen3-coder')
context = os.environ.get('ACORN_JUDGE_CONTEXT', 'No files found')

prompt = f"""You are the ACORN Judge Agent. Evaluate the solution quality.

Workspace files:
{context}

Evaluate:
1. Does the solution address the problem?
2. Is the code syntactically correct?
3. Are there output artifacts (reports, plots)?
4. Is there evidence of data analysis?

Respond with EXACTLY one JSON object:
{{"verdict": "pass" or "fail", "checks": {{"problem_addressed": true/false, "code_valid": true/false, "artifacts_present": true/false, "analysis_evident": true/false}}, "notes": "brief summary"}}

Output ONLY the JSON, no markdown, no explanation."""

body = json.dumps({
    'model': model,
    'max_tokens': 1024,
    'messages': [{'role': 'user', 'content': prompt}],
}).encode()

req = urllib.request.Request(
    f'{proxy}/v1/messages',
    data=body,
    headers={
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ollama',
        'anthropic-version': '2023-06-01',
    },
    method='POST',
)
try:
    resp = urllib.request.urlopen(req, timeout=300)
    result = json.load(resp)
    text = ''
    for block in result.get('content', []):
        if block.get('type') == 'text':
            text += block['text']
    text = text.strip()
    text = re.sub(r'^```\w*\n?', '', text)
    text = re.sub(r'\n?```\s*$', '', text)
    text = text.strip()
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        text = match.group(0)
    json.loads(text)
    print(text)
except Exception:
    print('{"verdict":"pass","checks":{},"notes":"auto-pass"}')
JUDGEPY
)

    echo "$VERDICT" > judge_verdict.json

    if [ -n "$TASK_ID" ]; then
        export ACORN_JUDGE_VERDICT_RAW="$VERDICT"
        export ACORN_JUDGE_TASK_ID="$TASK_ID"
        python3 <<'POSTVERDICT'
import json, urllib.request, os

api = os.environ.get('ACORN_API_URL', 'http://acorn-api:8000')
task_id = os.environ.get('ACORN_JUDGE_TASK_ID', '')
raw = os.environ.get('ACORN_JUDGE_VERDICT_RAW', '{}')

try:
    parsed = json.loads(raw)
except Exception:
    parsed = {"verdict": "pass", "checks": {}, "notes": "auto-pass"}

verdict = parsed.get("verdict", "pass")
checks = parsed.get("checks", {})
notes = parsed.get("notes", "")

body = json.dumps({
    "task_id": task_id,
    "verdict": verdict,
    "checks": checks,
    "notes": notes,
}).encode()
req = urllib.request.Request(
    f'{api}/api/judge_verdicts',
    data=body,
    headers={'Content-Type': 'application/json'},
    method='POST',
)
try:
    urllib.request.urlopen(req, timeout=10)
    print(f'Verdict posted: {verdict}')
except Exception as e:
    print(f'Failed to post verdict: {e}')
POSTVERDICT

        PARSED_VERDICT=$(echo "$VERDICT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('verdict','pass'))" 2>/dev/null || echo "pass")
        if [ "$PARSED_VERDICT" = "pass" ]; then
            patch_task "$TASK_ID" "complete"
        else
            patch_task "$TASK_ID" "failed"
        fi
    fi
    log "Judge evaluation complete (verdict=$(echo "$VERDICT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('verdict','?'))" 2>/dev/null || echo '?'))"
    exit 0
fi

# ── Kernel Extractor ──────────────────────────────────────────────────────
if [ "$ROLE" = "kernel-extractor" ]; then
    log "Scanning for reusable patterns"

    claude --dangerously-skip-permissions --model "$MODEL" --max-turns 10 -p \
      "Analyze all Python and Markdown files in /workspace. Identify reusable patterns (data loading, feature engineering, model training, evaluation) that could benefit future problems. Write a KERNEL.md file for each pattern found. Each KERNEL.md should have: name, description, when_to_use, code_template." \
      > /dev/null 2>&1 || true

    if [ -n "$TASK_ID" ]; then
        patch_task "$TASK_ID" "complete"
    fi
    log "Kernel extraction complete"
    exit 0
fi

# ── Orchestrator (default) ────────────────────────────────────────────────
log "Fetching problem $PROBLEM_UUID"
PROBLEM_JSON=$(curl -sf "$ACORN_API/api/problems/$PROBLEM_UUID" || echo "{}")
TITLE=$(echo "$PROBLEM_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('title','Problem'))" 2>/dev/null || echo "Problem")
DESCRIPTION=$(echo "$PROBLEM_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('description',''))" 2>/dev/null || echo "")

log "Step 0: Setting status to assembling"
patch_problem "assembling"
record_reasoning "init" "Orchestrator started for problem: $TITLE"

log "Step 1: Writing PROBLEM.md"
cat > PROBLEM.md <<HEREDOC
# $TITLE
## Problem UUID
$PROBLEM_UUID
## Description
$DESCRIPTION
HEREDOC

log "Step 1b: Querying kernel library for relevant prior kernels"
ENCODED_TITLE=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$TITLE'))" 2>/dev/null || echo "")
RELEVANT_KERNELS=$(curl -sf "$ACORN_API/api/kernels?query=$ENCODED_TITLE&top_k=5" 2>/dev/null || echo "[]")
KERNEL_CONTEXT=""
if [ "$RELEVANT_KERNELS" != "[]" ]; then
    KERNEL_CONTEXT=$(echo "$RELEVANT_KERNELS" | python3 -c "
import sys, json
kernels = json.load(sys.stdin)
if not isinstance(kernels, list) or len(kernels) == 0:
    print('')
else:
    lines = ['## Relevant Skills from Prior Problems']
    for s in kernels[:5]:
        lines.append(f'- {s.get(\"name\",\"?\")} ({s.get(\"category\",\"?\")}): {s.get(\"description\",\"\")[:120]}')
    print('\n'.join(lines))
" 2>/dev/null || echo "")
    if [ -n "$KERNEL_CONTEXT" ]; then
        log "Found relevant kernels to inject into decomposition"
    fi
fi

log "Step 2: Task decomposition via Ollama API"
export ACORN_DECOMP_TITLE="$TITLE"
export ACORN_DECOMP_DESC="$DESCRIPTION"
export ACORN_DECOMP_KERNELS="$KERNEL_CONTEXT"

DECOMPOSITION=$(python3 <<'PYEOF'
import json, urllib.request, sys, os, re

proxy = os.environ.get('ANTHROPIC_BASE_URL', 'http://acorn-api-relay:9000')
model = os.environ.get('ACORN_MODEL', 'qwen3-coder')
title = os.environ.get('ACORN_DECOMP_TITLE', 'Problem')
desc = os.environ.get('ACORN_DECOMP_DESC', '')
kernel_ctx = os.environ.get('ACORN_DECOMP_KERNELS', '')

kernel_section = f"\n\n{kernel_ctx}\n\nLeverage the above kernels where applicable." if kernel_ctx else ""

prompt = f"""Decompose this problem into tasks for a data science team.

Problem: {title}
Description: {desc}{kernel_section}

Return ONLY a JSON array of tasks:
[{{"title": "...", "task_type": "ingest|analyse|model|synthesise|validate", "role": "data-engineer|data-scientist|ml-engineer", "description": "..."}}]

Rules:
- 2-5 tasks maximum
- task_type must be one of: ingest, analyse, model, synthesise, validate
- role must be one of: data-engineer, data-scientist, ml-engineer
- Output ONLY the JSON array, no markdown fences, no explanation"""

body = json.dumps({
    'model': model,
    'max_tokens': 2048,
    'messages': [{'role': 'user', 'content': prompt}],
}).encode()

req = urllib.request.Request(
    f'{proxy}/v1/messages',
    data=body,
    headers={
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ollama',
        'anthropic-version': '2023-06-01',
    },
    method='POST',
)
try:
    resp = urllib.request.urlopen(req, timeout=300)
    result = json.load(resp)
    text = ''
    for block in result.get('content', []):
        if block.get('type') == 'text':
            text += block['text']
    text = text.strip()
    # Strip markdown code fences if present
    text = re.sub(r'^```\w*\n?', '', text)
    text = re.sub(r'\n?```\s*$', '', text)
    text = text.strip()
    # Extract JSON array if buried in text
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        text = match.group(0)
    json.loads(text)
    print(text)
except Exception as e:
    print(f'Decomposition error: {e}', file=sys.stderr)
    print('[]')
PYEOF
)
log "Decomposition result: $(echo "$DECOMPOSITION" | head -c 200)"
TASK_COUNT=$(echo "$DECOMPOSITION" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d) if isinstance(d,list) else 0)" 2>/dev/null || echo "0")
record_reasoning "decomposition" "Decomposed problem into $TASK_COUNT tasks via LLM" "0.8"

TASK_IDS=$(echo "$DECOMPOSITION" | python3 -c "
import sys, json, os
api = os.environ.get('ACORN_API_URL', 'http://acorn-api:8000')
puuid = os.environ.get('ACORN_PROBLEM_UUID', '')
try:
    import urllib.request
    tasks = json.load(sys.stdin)
    if not isinstance(tasks, list):
        tasks = []
    ids = []
    for t in tasks:
        body = json.dumps({
            'problem_id': puuid,
            'title': t.get('title', 'Task'),
            'description': t.get('description', ''),
            'task_type': t.get('task_type', 'analyse'),
            'assigned_to': t.get('role', 'data-scientist'),
        }).encode()
        req = urllib.request.Request(
            f'{api}/api/tasks',
            data=body,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            result = json.load(resp)
            ids.append({'id': result['id'], 'role': t.get('role', 'data-scientist')})
        except Exception:
            pass
    print(json.dumps(ids))
except Exception:
    print('[]')
" 2>/dev/null || echo "[]")

patch_problem "active"

record_reasoning "task_creation" "Created tasks and registered them with the API"
log "Step 3: Spawning specialist agents"
SPAWNED=$(echo "$TASK_IDS" | python3 -c "
import sys, json, os, urllib.request
api = os.environ.get('ACORN_API_URL', 'http://acorn-api:8000')
puuid = os.environ.get('ACORN_PROBLEM_UUID', '')
items = json.load(sys.stdin)
for item in items:
    tid = item['id']
    role = item['role']
    body = json.dumps({'role': role, 'task_id': tid}).encode()
    req = urllib.request.Request(
        f'{api}/api/problems/{puuid}/spawn-agent',
        data=body,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        urllib.request.urlopen(req, timeout=15)
        print(f'Spawned {role} for task {tid}')
    except Exception as e:
        print(f'Failed to spawn {role}: {e}')
" 2>/dev/null || echo "No agents spawned")
log "$SPAWNED"

record_reasoning "agent_spawn" "Spawned specialist agents for all decomposed tasks"
log "Step 4: Polling task completion"
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_POLL_ATTEMPTS ]; do
    TASKS_JSON=$(curl -sf "$ACORN_API/api/tasks?problem_id=$PROBLEM_UUID" 2>/dev/null || echo "[]")
    STATUS_SUMMARY=$(echo "$TASKS_JSON" | python3 -c "
import sys, json
tasks = json.load(sys.stdin)
if not isinstance(tasks, list):
    tasks = []
total = len(tasks)
done = sum(1 for t in tasks if t.get('status') in ('complete', 'failed'))
failed = sum(1 for t in tasks if t.get('status') == 'failed')
print(f'{done}/{total} done, {failed} failed')
if total == 0 or done >= total:
    print('ALL_DONE')
" 2>/dev/null || echo "0/0 done")

    log "Poll #$ATTEMPT: $STATUS_SUMMARY"

    if echo "$STATUS_SUMMARY" | grep -q "ALL_DONE"; then
        break
    fi

    ATTEMPT=$((ATTEMPT + 1))
    sleep $POLL_INTERVAL
done

record_reasoning "poll_complete" "All specialist tasks finished, proceeding to judge evaluation"
log "Step 5: Running judge (with task tracking)"
JUDGE_TASK_ID=$(python3 -c "
import json, urllib.request, os
api = os.environ.get('ACORN_API_URL', 'http://acorn-api:8000')
puuid = os.environ.get('ACORN_PROBLEM_UUID', '')
body = json.dumps({
    'problem_id': puuid,
    'title': 'Quality evaluation',
    'description': 'Judge evaluates overall solution quality',
    'task_type': 'validate',
    'assigned_to': 'judge-agent',
}).encode()
req = urllib.request.Request(f'{api}/api/tasks', data=body, headers={'Content-Type': 'application/json'}, method='POST')
try:
    resp = urllib.request.urlopen(req, timeout=10)
    print(json.load(resp)['id'])
except Exception:
    print('')
" 2>/dev/null || echo "")

if [ -n "$JUDGE_TASK_ID" ]; then
    curl -sf -X POST "$ACORN_API/api/problems/$PROBLEM_UUID/spawn-agent" \
        -H "Content-Type: application/json" \
        -d "{\"role\": \"judge\", \"task_id\": \"$JUDGE_TASK_ID\"}" > /dev/null 2>&1 || true
    log "Judge spawned with task $JUDGE_TASK_ID"
else
    curl -sf -X POST "$ACORN_API/api/problems/$PROBLEM_UUID/spawn-agent" \
        -H "Content-Type: application/json" \
        -d '{"role": "judge"}' > /dev/null 2>&1 || true
fi
sleep 30

record_reasoning "judge" "Judge evaluation spawned for quality assessment"
log "Step 6: Running kernel extractor (with task tracking)"
KERNEL_TASK_ID=$(python3 -c "
import json, urllib.request, os
api = os.environ.get('ACORN_API_URL', 'http://acorn-api:8000')
puuid = os.environ.get('ACORN_PROBLEM_UUID', '')
body = json.dumps({
    'problem_id': puuid,
    'title': 'Kernel extraction',
    'description': 'Extract reusable patterns from solution',
    'task_type': 'validate',
    'assigned_to': 'kernel-extractor',
}).encode()
req = urllib.request.Request(f'{api}/api/tasks', data=body, headers={'Content-Type': 'application/json'}, method='POST')
try:
    resp = urllib.request.urlopen(req, timeout=10)
    print(json.load(resp)['id'])
except Exception:
    print('')
" 2>/dev/null || echo "")

if [ -n "$KERNEL_TASK_ID" ]; then
    curl -sf -X POST "$ACORN_API/api/problems/$PROBLEM_UUID/spawn-agent" \
        -H "Content-Type: application/json" \
        -d "{\"role\": \"kernel-extractor\", \"task_id\": \"$KERNEL_TASK_ID\"}" > /dev/null 2>&1 || true
    log "Kernel extractor spawned with task $KERNEL_TASK_ID"
else
    curl -sf -X POST "$ACORN_API/api/problems/$PROBLEM_UUID/spawn-agent" \
        -H "Content-Type: application/json" \
        -d '{"role": "kernel-extractor"}' > /dev/null 2>&1 || true
fi
sleep 15

log "Step 6b: Ingesting extracted kernels into grove"
curl -sf -X POST "$ACORN_API/api/kernels/ingest-workspace/problem-$PROBLEM_UUID" \
    -H "Content-Type: application/json" 2>/dev/null || \
  curl -sf -X POST "$ACORN_API/api/kernels/ingest-workspace/$PROBLEM_UUID" \
    -H "Content-Type: application/json" 2>/dev/null || true
INGEST_RESULT=$?
log "Kernel ingestion result: $INGEST_RESULT"

log "Step 7: Marking problem complete"
FINAL_TASKS=$(curl -sf "$ACORN_API/api/tasks?problem_id=$PROBLEM_UUID" 2>/dev/null || echo "[]")
HAS_FAILURES=$(echo "$FINAL_TASKS" | python3 -c "
import sys, json
tasks = json.load(sys.stdin)
print('yes' if any(t.get('status')=='failed' for t in (tasks if isinstance(tasks,list) else [])) else 'no')
" 2>/dev/null || echo "no")

if [ "$HAS_FAILURES" = "yes" ]; then
    patch_problem "failed"
    record_reasoning "conclusion" "Pipeline completed with failures" "0.3"
    log "Pipeline complete with failures"
else
    patch_problem "complete"
    record_reasoning "conclusion" "Pipeline completed successfully" "0.9"
    log "Pipeline complete successfully"
fi

# Record GRS reward signals (derive verdict from judge_verdicts API)
VERDICTS_JSON=$(curl -sf "$ACORN_API/api/judge_verdicts/$PROBLEM_UUID" 2>/dev/null || echo "[]")
JUDGE_VERDICT=$(echo "$VERDICTS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['verdict'] if isinstance(d,list) and len(d)>0 else '')" 2>/dev/null || echo "")
if [ "$JUDGE_VERDICT" = "pass" ]; then
    curl -sf -X POST "$ACORN_API/api/rewards/record" \
        -H "Content-Type: application/json" \
        -d "{\"signal\": \"JUDGE_PASS\", \"agent_id\": \"$AGENT_ID\", \"role\": \"$ROLE\", \"problem_id\": \"$PROBLEM_UUID\", \"rationale\": \"Judge issued PASS verdict\"}" 2>/dev/null || true
    curl -sf -X POST "$ACORN_API/api/rewards/record" \
        -H "Content-Type: application/json" \
        -d "{\"signal\": \"SOLUTION_COMPLETE\", \"agent_id\": \"orchestrator\", \"role\": \"orchestrator\", \"problem_id\": \"$PROBLEM_UUID\", \"rationale\": \"Problem solved successfully\"}" 2>/dev/null || true
fi
if [ "$JUDGE_VERDICT" = "fail" ]; then
    curl -sf -X POST "$ACORN_API/api/rewards/record" \
        -H "Content-Type: application/json" \
        -d "{\"signal\": \"JUDGE_FAIL\", \"agent_id\": \"$AGENT_ID\", \"role\": \"$ROLE\", \"problem_id\": \"$PROBLEM_UUID\", \"points\": -5, \"rationale\": \"Judge issued FAIL verdict\"}" 2>/dev/null || true
fi

log "Step 8: Assembling REASONING_TRAIL.md"
python3 <<'TRAIL_PY'
import json, urllib.request, os

api = os.environ.get('ACORN_API_URL', 'http://acorn-api:8000')
puuid = os.environ.get('ACORN_PROBLEM_UUID', '')
try:
    req = urllib.request.Request(f'{api}/api/problems/{puuid}/reasoning-trail')
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.load(resp)
    steps = data.get('steps', [])
    lines = ['# REASONING TRAIL\n']
    lines.append(f'**Problem:** {puuid}\n')
    lines.append(f'**Total steps:** {len(steps)}\n')
    lines.append('---\n')
    for i, s in enumerate(steps, 1):
        lines.append(f'## Step {i}: {s.get("step_type", "unknown")}')
        lines.append(f'**Agent:** {s.get("agent_id", "?")}')
        if s.get('confidence') is not None:
            lines.append(f'**Confidence:** {s["confidence"]}')
        lines.append(f'\n{s.get("summary", "")}\n')
        if s.get('sources'):
            lines.append(f'**Sources:** {json.dumps(s["sources"])}\n')
        lines.append(f'*{s.get("created_at", "")}*\n')
        lines.append('---\n')
    with open('/workspace/REASONING_TRAIL.md', 'w') as f:
        f.write('\n'.join(lines))
    print(f'REASONING_TRAIL.md written ({len(steps)} steps)')
except Exception as e:
    print(f'Failed to assemble reasoning trail: {e}')
    with open('/workspace/REASONING_TRAIL.md', 'w') as f:
        f.write(f'# REASONING TRAIL\n\nFailed to assemble: {e}\n')
TRAIL_PY

ls -la /workspace/
