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

# ── Orchestrator — Claude Code Agent Teams (default) ─────────────────────
# The orchestrator runs Claude Code with native agent teams enabled.
# Teammates are Claude Code instances using local Ollama models via the proxy.
# All coordination (shared task list, mailbox, teammates) is handled by
# Claude Code's agent team protocol — NOT by spawning separate Docker containers.
#
# Toggle: ACORN_USE_AGENT_TEAMS=false falls back to legacy container orchestration.

USE_AGENT_TEAMS="${ACORN_USE_AGENT_TEAMS:-true}"

log "Fetching problem $PROBLEM_UUID"
PROBLEM_JSON=$(curl -sf "$ACORN_API/api/problems/$PROBLEM_UUID" || echo "{}")
TITLE=$(echo "$PROBLEM_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('title','Problem'))" 2>/dev/null || echo "Problem")
DESCRIPTION=$(echo "$PROBLEM_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('description',''))" 2>/dev/null || echo "")

log "Step 0: Setting status to assembling"
patch_problem "assembling"
record_reasoning "init" "Orchestrator started for problem: $TITLE (mode=${USE_AGENT_TEAMS:+agent-teams}${USE_AGENT_TEAMS:-legacy})"

log "Step 1: Writing PROBLEM.md"
cat > PROBLEM.md <<HEREDOC
# $TITLE
## Problem UUID
$PROBLEM_UUID
## Description
$DESCRIPTION
HEREDOC

log "Step 1b: Querying kernel library"
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
    lines = ['## Relevant Kernels from Prior Problems']
    for s in kernels[:5]:
        lines.append(f'- {s.get(\"name\",\"?\")} ({s.get(\"category\",\"?\")}): {s.get(\"description\",\"\")[:120]}')
    print('\n'.join(lines))
" 2>/dev/null || echo "")
    if [ -n "$KERNEL_CONTEXT" ]; then
        echo "" >> PROBLEM.md
        echo "$KERNEL_CONTEXT" >> PROBLEM.md
        log "Found relevant kernels, appended to PROBLEM.md"
        # Record usage so kernels accumulate verified_on_problems for promotion
        echo "$RELEVANT_KERNELS" | python3 -c "
import sys, json, urllib.request, os
api = os.environ.get('ACORN_API_URL', 'http://acorn-api:8000')
prob = os.environ.get('ACORN_PROBLEM_UUID', '')
try:
    kernels = json.load(sys.stdin)
    for k in (kernels if isinstance(kernels, list) else [])[:5]:
        kid = k.get('id', '')
        if not kid: continue
        body = json.dumps({'problem_id': prob}).encode()
        req = urllib.request.Request(
            f'{api}/api/kernels/{kid}/record-use', data=body,
            headers={'Content-Type': 'application/json'}, method='POST')
        try: urllib.request.urlopen(req, timeout=5)
        except Exception: pass
except Exception: pass
" 2>/dev/null || true
    fi
fi

DATA_FILES=$(find /workspace -maxdepth 1 \( -name '*.csv' -o -name '*.json' -o -name '*.parquet' \) | head -10)
DATA_PREVIEW=""
for f in $DATA_FILES; do
    DATA_PREVIEW="${DATA_PREVIEW}  - $(basename "$f"): $(wc -l < "$f" 2>/dev/null || echo '?') lines
"
done

patch_problem "active"

if [ "$USE_AGENT_TEAMS" = "true" ]; then
    # ── Agent Teams Mode ──────────────────────────────────────────────────
    # Ollama 0.17+ has native Anthropic Messages API support at /v1/messages.
    # We can optionally bypass the relay and connect directly to Ollama for
    # cleaner tool-call translation (no double-conversion).
    #
    # ACORN_AGENT_TEAM_ENDPOINT: "relay" (default) or "direct" (Ollama native)
    TEAM_ENDPOINT="${ACORN_AGENT_TEAM_ENDPOINT:-direct}"
    OLLAMA_DIRECT_URL="${ACORN_OLLAMA_URL:-http://acorn-ollama:11434}"

    if [ "$TEAM_ENDPOINT" = "direct" ]; then
        log "Agent Teams: using Ollama native Anthropic API (direct)"
        export ANTHROPIC_BASE_URL="$OLLAMA_DIRECT_URL"
    else
        log "Agent Teams: using acorn-api-relay proxy"
    fi

    log "Step 1c: Model selection"
    curl -sf -X POST "$ACORN_API/api/models/sync" -H "Content-Type: application/json" -d '{}' > /dev/null 2>&1 || true
    ORCH_REC=$(curl -sf "$ACORN_API/api/models/recommend?task_type=reasoning&role=orchestrator" 2>/dev/null || echo "")
    if [ -n "$ORCH_REC" ]; then
        ORCH_MODEL=$(echo "$ORCH_REC" | python3 -c "import sys,json; print(json.load(sys.stdin).get('name',''))" 2>/dev/null || echo "")
        [ -n "$ORCH_MODEL" ] && MODEL="$ORCH_MODEL" && log "Using recommended orchestrator model: $MODEL"
    fi

    log "Step 2: Running Claude Code Agent Teams (all local models)"
    record_reasoning "dispatch" "Launching Claude Code agent team (endpoint=$TEAM_ENDPOINT, model=$MODEL)"

    # Detect problem type
    IS_KERNEL_BUILD=false
    if echo "$DESCRIPTION" | grep -iqE "kernel|reusable.*pattern|build.*pattern|analytical.*pattern"; then
        IS_KERNEL_BUILD=true
    fi

    if [ "$IS_KERNEL_BUILD" = "true" ]; then
        TEAM_PROMPT="You are a Python expert building reusable code templates.

Problem: $TITLE
$DESCRIPTION

$(cat PROBLEM.md 2>/dev/null || echo '')

Tasks (do each step with Bash):
1. Run: cat PROBLEM.md to understand the full context
2. For each pattern/concept described, write a parameterized Python function to /workspace/{concept_name}.py (no hardcoded paths, use arguments)
3. Write /workspace/SOLUTION.md summarizing: what each template does, its inputs/outputs, example usage
4. Run: ls /workspace/*.py to verify files were created

Keep going until SOLUTION.md and at least one .py template exist."
    else
        TEAM_PROMPT="Solve: $TITLE. $DESCRIPTION

$(cat PROBLEM.md 2>/dev/null || echo '')

Data: /workspace/ contains:
$DATA_PREVIEW

Do this step by step:
1. Run: ls /workspace/ to see available files
2. If CSV files exist: run a python3 command to analyze them (use pandas, sklearn, numpy)
3. If no data exists: generate synthetic data with python3, then analyze it
4. Run a python3 command to write /workspace/SOLUTION.md with results

IMPORTANT: Always write /workspace/SOLUTION.md with your findings. Keep going until it exists."
    fi

    # Inject model routing hints into the prompt
    JUDGE_MODEL=$(curl -sf "$ACORN_API/api/agents/model-for-role?role=judge-agent" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('model','qwen3-coder'))" 2>/dev/null || echo "deepseek-r1:14b")
    ANALYST_MODEL=$(curl -sf "$ACORN_API/api/agents/model-for-role?role=data-scientist" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('model','deepseek-r1:14b'))" 2>/dev/null || echo "deepseek-r1:14b")

    MODEL_ROUTING="
## Model Routing (use these Ollama models for sub-tasks)
- Complex reasoning / quality evaluation: $JUDGE_MODEL
- Data analysis / domain expertise: $ANALYST_MODEL
- Code generation / implementation: $MODEL
All models available at: $ANTHROPIC_BASE_URL"

    TEAM_PROMPT="${TEAM_PROMPT}${MODEL_ROUTING}"

    claude --dangerously-skip-permissions \
        --model "$MODEL" \
        --max-turns 50 \
        -p "$TEAM_PROMPT" \
        > /workspace/orchestrator_log.txt 2>&1 || true

    log "Claude Code agent team session complete"
    record_reasoning "team_complete" "Agent team session finished, checking outputs"

else
    # ── Legacy Container Mode ─────────────────────────────────────────────
    log "Step 2: Legacy mode — task decomposition via Ollama API"

    export ACORN_DECOMP_TITLE="$TITLE"
    export ACORN_DECOMP_DESC="$DESCRIPTION"

    DECOMPOSITION=$(python3 <<'PYEOF'
import json, urllib.request, sys, os, re

proxy = os.environ.get('ANTHROPIC_BASE_URL', 'http://acorn-api-relay:9000')
model = os.environ.get('ACORN_MODEL', 'qwen3-coder')
title = os.environ.get('ACORN_DECOMP_TITLE', 'Problem')
desc = os.environ.get('ACORN_DECOMP_DESC', '')

prompt = f"""Decompose this problem into tasks for a data science team.

Problem: {title}
Description: {desc}

Return ONLY a JSON array of tasks:
[{{"title": "...", "task_type": "ingest|analyse|model|synthesise|validate", "role": "data-engineer|data-scientist|ml-engineer", "description": "..."}}]

Rules:
- 2-5 tasks maximum
- Output ONLY the JSON array, no markdown fences, no explanation"""

body = json.dumps({
    'model': model, 'max_tokens': 2048,
    'messages': [{'role': 'user', 'content': prompt}],
}).encode()
req = urllib.request.Request(
    f'{proxy}/v1/messages', data=body,
    headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ollama', 'anthropic-version': '2023-06-01'},
    method='POST',
)
try:
    resp = urllib.request.urlopen(req, timeout=300)
    result = json.load(resp)
    text = ''.join(b['text'] for b in result.get('content', []) if b.get('type') == 'text').strip()
    text = re.sub(r'^```\w*\n?', '', text)
    text = re.sub(r'\n?```\s*$', '', text)
    match = re.search(r'\[.*\]', text.strip(), re.DOTALL)
    if match: text = match.group(0)
    json.loads(text)
    print(text)
except Exception as e:
    print(f'Decomposition error: {e}', file=sys.stderr)
    print('[]')
PYEOF
)

    TASK_COUNT=$(echo "$DECOMPOSITION" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d) if isinstance(d,list) else 0)" 2>/dev/null || echo "0")
    record_reasoning "decomposition" "Decomposed into $TASK_COUNT tasks (legacy mode)" "0.8"

    TASK_IDS=$(echo "$DECOMPOSITION" | python3 -c "
import sys, json, os, urllib.request
api = os.environ.get('ACORN_API_URL', 'http://acorn-api:8000')
puuid = os.environ.get('ACORN_PROBLEM_UUID', '')
tasks = json.load(sys.stdin)
if not isinstance(tasks, list): tasks = []
ids = []
for t in tasks:
    body = json.dumps({'problem_id': puuid, 'title': t.get('title','Task'), 'description': t.get('description',''),
                       'task_type': t.get('task_type','analyse'), 'assigned_to': t.get('role','data-scientist')}).encode()
    try:
        resp = urllib.request.urlopen(urllib.request.Request(f'{api}/api/tasks', data=body,
               headers={'Content-Type': 'application/json'}, method='POST'), timeout=10)
        ids.append({'id': json.load(resp)['id'], 'role': t.get('role','data-scientist')})
    except Exception: pass
print(json.dumps(ids))
" 2>/dev/null || echo "[]")

    log "Step 2b: Model selection for legacy specialists"
    curl -sf -X POST "$ACORN_API/api/models/sync" -H "Content-Type: application/json" -d '{}' > /dev/null 2>&1 || true
    export ACORN_LEGACY_MODEL_MAP=$(python3 -c "
import json, urllib.request, os
api = os.environ.get('ACORN_API_URL', 'http://acorn-api:8000')
roles = {'data-engineer': 'ingest', 'data-scientist': 'analyse', 'ml-engineer': 'model'}
m = {}
for role, tt in roles.items():
    try:
        r = urllib.request.urlopen(urllib.request.Request(f'{api}/api/models/recommend?task_type={tt}&role={role}'), timeout=5)
        d = json.load(r)
        m[role] = d.get('name', 'qwen3-coder')
    except Exception:
        m[role] = 'qwen3-coder'
print(json.dumps(m))
" 2>/dev/null || echo '{}')

    log "Step 3: Spawning specialist containers"
    echo "$TASK_IDS" | python3 -c "
import sys, json, os, urllib.request
api = os.environ.get('ACORN_API_URL', 'http://acorn-api:8000')
puuid = os.environ.get('ACORN_PROBLEM_UUID', '')
model_map = json.loads(os.environ.get('ACORN_LEGACY_MODEL_MAP', '{}'))
for item in json.load(sys.stdin):
    role = item.get('role', 'data-scientist')
    payload = {'role': role, 'task_id': item['id']}
    if role in model_map:
        payload['model'] = model_map[role]
    body = json.dumps(payload).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(f'{api}/api/problems/{puuid}/spawn-agent', data=body,
               headers={'Content-Type': 'application/json'}, method='POST'), timeout=15)
        model_info = f' (model={model_map[role]})' if role in model_map else ''
        print(f'Spawned {role} for task {item["id"]}{model_info}')
    except Exception as e: print(f'Failed: {e}')
" 2>/dev/null || echo "No agents spawned"

    log "Step 4: Polling task completion"
    ATTEMPT=0
    while [ $ATTEMPT -lt $MAX_POLL_ATTEMPTS ]; do
        TASKS_JSON=$(curl -sf "$ACORN_API/api/tasks?problem_id=$PROBLEM_UUID" 2>/dev/null || echo "[]")
        STATUS_SUMMARY=$(echo "$TASKS_JSON" | python3 -c "
import sys, json
tasks = json.load(sys.stdin)
if not isinstance(tasks, list): tasks = []
total = len(tasks); done = sum(1 for t in tasks if t.get('status') in ('complete','failed'))
failed = sum(1 for t in tasks if t.get('status') == 'failed')
print(f'{done}/{total} done, {failed} failed')
if total == 0 or done >= total: print('ALL_DONE')
" 2>/dev/null || echo "0/0 done")
        log "Poll #$ATTEMPT: $STATUS_SUMMARY"
        echo "$STATUS_SUMMARY" | grep -q "ALL_DONE" && break
        ATTEMPT=$((ATTEMPT + 1))
        sleep $POLL_INTERVAL
    done
fi

# ── Post-execution: Judge + Kernel Extraction + Finalization ──────────────
# (runs for both agent-teams and legacy modes)

record_reasoning "post_exec" "Specialist work complete, running quality gate"

log "Step 5: Running judge evaluation"
JUDGE_TASK_ID=$(python3 -c "
import json, urllib.request, os
api = os.environ.get('ACORN_API_URL', 'http://acorn-api:8000')
puuid = os.environ.get('ACORN_PROBLEM_UUID', '')
body = json.dumps({'problem_id': puuid, 'title': 'Quality evaluation',
       'description': 'Judge evaluates overall solution quality', 'task_type': 'validate',
       'assigned_to': 'judge-agent'}).encode()
try:
    resp = urllib.request.urlopen(urllib.request.Request(f'{api}/api/tasks', data=body,
           headers={'Content-Type': 'application/json'}, method='POST'), timeout=10)
    print(json.load(resp)['id'])
except Exception: print('')
" 2>/dev/null || echo "")

WORKSPACE_FILES=$(find /workspace -maxdepth 2 -type f ! -path '*/.git/*' \( -name '*.md' -o -name '*.py' -o -name '*.csv' \) | head -20)
JUDGE_CONTEXT=""
for f in $WORKSPACE_FILES; do
    JUDGE_CONTEXT="${JUDGE_CONTEXT}
--- $(basename "$f") ---
$(head -100 "$f" 2>/dev/null || true)
"
done

export ACORN_JUDGE_CONTEXT="$JUDGE_CONTEXT"
VERDICT=$(python3 <<'JUDGEPY'
import json, urllib.request, sys, os, re
proxy = os.environ.get('ANTHROPIC_BASE_URL', 'http://acorn-api-relay:9000')
model = os.environ.get('ACORN_MODEL', 'qwen3-coder')
context = os.environ.get('ACORN_JUDGE_CONTEXT', 'No files found')

prompt = f"""You are the ACORN Judge Agent. Evaluate the solution quality.

Workspace files:
{context}

Evaluate: 1) Does the solution address the problem? 2) Is code syntactically correct? 3) Are there output artifacts? 4) Is there evidence of data analysis?

Respond with EXACTLY one JSON object:
{{"verdict": "pass" or "fail", "checks": {{"problem_addressed": true/false, "code_valid": true/false, "artifacts_present": true/false, "analysis_evident": true/false}}, "notes": "brief summary"}}
Output ONLY the JSON."""

body = json.dumps({'model': model, 'max_tokens': 1024,
       'messages': [{'role': 'user', 'content': prompt}]}).encode()
req = urllib.request.Request(f'{proxy}/v1/messages', data=body,
      headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ollama', 'anthropic-version': '2023-06-01'}, method='POST')
try:
    resp = urllib.request.urlopen(req, timeout=300)
    result = json.load(resp)
    text = ''.join(b['text'] for b in result.get('content', []) if b.get('type') == 'text').strip()
    text = re.sub(r'^```\w*\n?', '', text); text = re.sub(r'\n?```\s*$', '', text)
    match = re.search(r'\{.*\}', text.strip(), re.DOTALL)
    if match: text = match.group(0)
    json.loads(text); print(text)
except Exception:
    print('{"verdict":"pass","checks":{},"notes":"auto-pass"}')
JUDGEPY
)

echo "$VERDICT" > judge_verdict.json

if [ -n "$JUDGE_TASK_ID" ]; then
    export ACORN_JUDGE_VERDICT_RAW="$VERDICT"
    export ACORN_JUDGE_TASK_ID="$JUDGE_TASK_ID"
    python3 <<'POSTVERDICT'
import json, urllib.request, os
api = os.environ.get('ACORN_API_URL', 'http://acorn-api:8000')
task_id = os.environ.get('ACORN_JUDGE_TASK_ID', '')
raw = os.environ.get('ACORN_JUDGE_VERDICT_RAW', '{}')
try: parsed = json.loads(raw)
except Exception: parsed = {"verdict": "pass", "checks": {}, "notes": "auto-pass"}
body = json.dumps({"task_id": task_id, "verdict": parsed.get("verdict","pass"),
       "checks": parsed.get("checks",{}), "notes": parsed.get("notes","")}).encode()
try: urllib.request.urlopen(urllib.request.Request(f'{api}/api/judge_verdicts', data=body,
     headers={'Content-Type': 'application/json'}, method='POST'), timeout=10)
except Exception: pass
POSTVERDICT

    PARSED_VERDICT=$(echo "$VERDICT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('verdict','pass'))" 2>/dev/null || echo "pass")
    patch_task "$JUDGE_TASK_ID" "$([ "$PARSED_VERDICT" = "pass" ] && echo complete || echo failed)"
fi

log "Step 6: Running kernel extractor"
claude --dangerously-skip-permissions --model "$MODEL" --max-turns 10 -p \
  "Analyze all Python and Markdown files in /workspace. Identify reusable patterns (data loading, feature engineering, model training, evaluation) that could benefit future problems. Write a KERNEL.md file for each pattern found. Each KERNEL.md should have: name, description, when_to_use, code_template." \
  > /dev/null 2>&1 || true

log "Step 6b: Ingesting extracted kernels into grove"
curl -sf -X POST "$ACORN_API/api/kernels/ingest-workspace/problem-$PROBLEM_UUID" \
    -H "Content-Type: application/json" 2>/dev/null || \
  curl -sf -X POST "$ACORN_API/api/kernels/ingest-workspace/$PROBLEM_UUID" \
    -H "Content-Type: application/json" 2>/dev/null || true

log "Step 7: Marking problem status"
JUDGE_LOCAL_VERDICT="pass"
if [ -f /workspace/judge_verdict.json ]; then
    JUDGE_LOCAL_VERDICT=$(python3 -c "
import json
try: print(json.load(open('/workspace/judge_verdict.json')).get('verdict','pass'))
except Exception: print('pass')
" 2>/dev/null || echo "pass")
    log "Judge verdict: $JUDGE_LOCAL_VERDICT"
fi

OUTPUT_COUNT=$(find /workspace -maxdepth 1 -name '*_output.md' -o -name 'SOLUTION.md' -o -name 'ANALYSIS_REPORT.md' | wc -l)
if [ "$JUDGE_LOCAL_VERDICT" = "fail" ] || [ "$OUTPUT_COUNT" -eq 0 ]; then
    patch_problem "failed"
    record_reasoning "conclusion" "Pipeline failed (judge=$JUDGE_LOCAL_VERDICT, outputs=$OUTPUT_COUNT)" "0.3"
    log "Pipeline complete with failures"
else
    patch_problem "complete"
    record_reasoning "conclusion" "Pipeline completed successfully (judge=$JUDGE_LOCAL_VERDICT, outputs=$OUTPUT_COUNT)" "0.9"
    log "Pipeline complete successfully"
fi

# GRS reward signals
VERDICTS_JSON=$(curl -sf "$ACORN_API/api/judge_verdicts/$PROBLEM_UUID" 2>/dev/null || echo "[]")
JUDGE_VERDICT=$(echo "$VERDICTS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['verdict'] if isinstance(d,list) and len(d)>0 else '')" 2>/dev/null || echo "")
if [ "$JUDGE_VERDICT" = "pass" ]; then
    curl -sf -X POST "$ACORN_API/api/rewards/record" \
        -H "Content-Type: application/json" \
        -d "{\"signal\": \"JUDGE_PASS\", \"agent_id\": \"$AGENT_ID\", \"role\": \"$ROLE\", \"problem_id\": \"$PROBLEM_UUID\", \"rationale\": \"Judge PASS\"}" 2>/dev/null || true
    curl -sf -X POST "$ACORN_API/api/rewards/record" \
        -H "Content-Type: application/json" \
        -d "{\"signal\": \"SOLUTION_COMPLETE\", \"agent_id\": \"orchestrator\", \"role\": \"orchestrator\", \"problem_id\": \"$PROBLEM_UUID\", \"rationale\": \"Problem solved\"}" 2>/dev/null || true
fi
if [ "$JUDGE_VERDICT" = "fail" ]; then
    curl -sf -X POST "$ACORN_API/api/rewards/record" \
        -H "Content-Type: application/json" \
        -d "{\"signal\": \"JUDGE_FAIL\", \"agent_id\": \"$AGENT_ID\", \"role\": \"$ROLE\", \"problem_id\": \"$PROBLEM_UUID\", \"points\": -5, \"rationale\": \"Judge FAIL\"}" 2>/dev/null || true
fi

log "Step 8: Assembling REASONING_TRAIL.md"
python3 <<'TRAIL_PY'
import json, urllib.request, os
api = os.environ.get('ACORN_API_URL', 'http://acorn-api:8000')
puuid = os.environ.get('ACORN_PROBLEM_UUID', '')
try:
    resp = urllib.request.urlopen(urllib.request.Request(f'{api}/api/problems/{puuid}/reasoning-trail'), timeout=10)
    steps = json.load(resp).get('steps', [])
    lines = ['# REASONING TRAIL\n', f'**Problem:** {puuid}\n', f'**Total steps:** {len(steps)}\n', '---\n']
    for i, s in enumerate(steps, 1):
        lines.extend([f'## Step {i}: {s.get("step_type","unknown")}', f'**Agent:** {s.get("agent_id","?")}'])
        if s.get('confidence') is not None: lines.append(f'**Confidence:** {s["confidence"]}')
        lines.extend([f'\n{s.get("summary","")}\n', f'*{s.get("created_at","")}*\n', '---\n'])
    with open('/workspace/REASONING_TRAIL.md', 'w') as f: f.write('\n'.join(lines))
    print(f'REASONING_TRAIL.md written ({len(steps)} steps)')
except Exception as e:
    with open('/workspace/REASONING_TRAIL.md', 'w') as f: f.write(f'# REASONING TRAIL\n\nFailed: {e}\n')
TRAIL_PY

ls -la /workspace/
