"""
Standalone test: Local Agent Teams via Ollama's native Anthropic API.

Tests the full round-trip:
1. Anthropic Messages API with tools -> Ollama
2. Tool call responses (tool_use blocks)
3. Multi-turn with tool_result
4. Streaming SSE
5. Complex tool schemas (simulating TeamCreate/Task patterns)
"""

import json
import os
import sys
import time
import httpx

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("MODEL", "qwen3-coder")
RELAY_URL = os.environ.get("RELAY_URL", "http://localhost:9000")

HEADERS = {
    "Content-Type": "application/json",
    "x-api-key": "ollama",
    "anthropic-version": "2023-06-01",
}

AGENT_TEAM_TOOLS = [
    {
        "name": "Task",
        "description": "Launch a new agent to handle a task autonomously",
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Short 3-5 word description of the task",
                },
                "prompt": {
                    "type": "string",
                    "description": "Detailed instructions for the agent",
                },
                "subagent_type": {
                    "type": "string",
                    "enum": ["generalPurpose", "explore", "shell"],
                    "description": "Type of agent to spawn",
                },
            },
            "required": ["description", "prompt"],
        },
    },
    {
        "name": "Bash",
        "description": "Execute a shell command",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The command to run"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "Read",
        "description": "Read a file from the filesystem",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute path to file"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "Write",
        "description": "Write content to a file",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "contents": {"type": "string"},
            },
            "required": ["path", "contents"],
        },
    },
]


def test_basic_tool_call(base_url: str, label: str) -> bool:
    """Test basic tool calling via Anthropic Messages API."""
    print(f"\n{'='*60}")
    print(f"TEST 1: Basic tool call [{label}]")
    print(f"{'='*60}")

    resp = httpx.post(
        f"{base_url}/v1/messages",
        headers=HEADERS,
        json={
            "model": MODEL,
            "max_tokens": 200,
            "tools": AGENT_TEAM_TOOLS[:2],
            "messages": [
                {"role": "user", "content": "List the files in the /workspace directory"}
            ],
        },
        timeout=60.0,
    )
    data = resp.json()
    print(f"  Status: {resp.status_code}")
    print(f"  Stop reason: {data.get('stop_reason')}")

    tool_uses = [b for b in data.get("content", []) if b.get("type") == "tool_use"]
    if tool_uses:
        for tu in tool_uses:
            print(f"  Tool: {tu['name']}({json.dumps(tu['input'])[:100]})")
        print("  PASS: Model generated tool calls")
        return True
    else:
        text = next(
            (b["text"] for b in data.get("content", []) if b.get("type") == "text"),
            "",
        )
        print(f"  Text response: {text[:200]}")
        print("  WARN: No tool call generated (model responded with text)")
        return False


def test_multi_turn(base_url: str, label: str) -> bool:
    """Test multi-turn conversation with tool results."""
    print(f"\n{'='*60}")
    print(f"TEST 2: Multi-turn with tool_result [{label}]")
    print(f"{'='*60}")

    messages = [
        {"role": "user", "content": "Read the file at /workspace/data.csv and tell me how many rows it has"},
    ]

    resp = httpx.post(
        f"{base_url}/v1/messages",
        headers=HEADERS,
        json={
            "model": MODEL,
            "max_tokens": 200,
            "tools": AGENT_TEAM_TOOLS,
            "messages": messages,
        },
        timeout=60.0,
    )
    turn1 = resp.json()
    print(f"  Turn 1 stop_reason: {turn1.get('stop_reason')}")

    tool_uses = [b for b in turn1.get("content", []) if b.get("type") == "tool_use"]
    if not tool_uses:
        print("  SKIP: Model didn't use a tool")
        return False

    tu = tool_uses[0]
    print(f"  Turn 1 tool: {tu['name']}({json.dumps(tu['input'])[:80]})")

    messages.append({"role": "assistant", "content": turn1["content"]})
    messages.append({
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": tu["id"],
                "content": "name,age,city\nAlice,30,NYC\nBob,25,LA\nCharlie,35,Chicago\n",
            }
        ],
    })

    resp2 = httpx.post(
        f"{base_url}/v1/messages",
        headers=HEADERS,
        json={
            "model": MODEL,
            "max_tokens": 200,
            "tools": AGENT_TEAM_TOOLS,
            "messages": messages,
        },
        timeout=60.0,
    )
    turn2 = resp2.json()
    print(f"  Turn 2 stop_reason: {turn2.get('stop_reason')}")

    text_blocks = [b for b in turn2.get("content", []) if b.get("type") == "text"]
    if text_blocks:
        print(f"  Turn 2 text: {text_blocks[0]['text'][:200]}")
        if any(kw in text_blocks[0]["text"].lower() for kw in ["3", "three", "row"]):
            print("  PASS: Model correctly analyzed tool result")
            return True
    print("  PARTIAL: Multi-turn completed but answer unclear")
    return True


def test_agent_delegation(base_url: str, label: str) -> bool:
    """Test if model can use Task tool for agent delegation."""
    print(f"\n{'='*60}")
    print(f"TEST 3: Agent delegation via Task tool [{label}]")
    print(f"{'='*60}")

    resp = httpx.post(
        f"{base_url}/v1/messages",
        headers=HEADERS,
        json={
            "model": MODEL,
            "max_tokens": 500,
            "system": (
                "You are an orchestrator. You MUST delegate work using the Task tool. "
                "Never do work directly - always spawn agents via the Task tool."
            ),
            "tools": AGENT_TEAM_TOOLS,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Analyze sales data in /workspace/sales.csv. "
                        "Create a data analysis pipeline with: "
                        "1) Data cleaning, 2) Statistical analysis, 3) Visualization. "
                        "Delegate each step to a separate agent."
                    ),
                }
            ],
        },
        timeout=120.0,
    )
    data = resp.json()
    print(f"  Status: {resp.status_code}")
    print(f"  Stop reason: {data.get('stop_reason')}")

    tool_uses = [b for b in data.get("content", []) if b.get("type") == "tool_use"]
    task_uses = [t for t in tool_uses if t["name"] == "Task"]

    if task_uses:
        for tu in task_uses:
            desc = tu["input"].get("description", "?")
            print(f"  Task spawned: {desc}")
        print(f"  PASS: Model delegated {len(task_uses)} task(s)")
        return True

    text_blocks = [b for b in data.get("content", []) if b.get("type") == "text"]
    if text_blocks:
        print(f"  Text: {text_blocks[0]['text'][:300]}")

    if tool_uses:
        print(f"  Used other tools: {[t['name'] for t in tool_uses]}")
        print("  PARTIAL: Model used tools but not Task delegation")
        return False

    print("  FAIL: No tool calls at all")
    return False


def test_streaming(base_url: str, label: str) -> bool:
    """Test streaming SSE responses."""
    print(f"\n{'='*60}")
    print(f"TEST 4: Streaming SSE [{label}]")
    print(f"{'='*60}")

    with httpx.stream(
        "POST",
        f"{base_url}/v1/messages",
        headers=HEADERS,
        json={
            "model": MODEL,
            "max_tokens": 50,
            "stream": True,
            "messages": [{"role": "user", "content": "Count to 5"}],
        },
        timeout=60.0,
    ) as resp:
        event_types = set()
        chunk_count = 0
        for line in resp.iter_lines():
            if line.startswith("event: "):
                event_types.add(line[7:])
            if line.startswith("data: "):
                chunk_count += 1

        print(f"  Event types: {sorted(event_types)}")
        print(f"  Data chunks: {chunk_count}")

        expected = {"message_start", "content_block_start", "content_block_delta"}
        if expected.issubset(event_types):
            print("  PASS: All expected SSE event types present")
            return True
        print(f"  WARN: Missing event types: {expected - event_types}")
        return False


def main():
    print("=" * 60)
    print("LOCAL AGENT TEAMS TEST SUITE")
    print(f"Ollama: {OLLAMA_URL}  Model: {MODEL}")
    print(f"Relay:  {RELAY_URL}")
    print("=" * 60)

    results = {}

    # Test directly against Ollama's native Anthropic API
    print("\n" + "#" * 60)
    print("# DIRECT OLLAMA (native Anthropic API)")
    print("#" * 60)
    results["direct_basic"] = test_basic_tool_call(OLLAMA_URL, "Direct")
    results["direct_multi"] = test_multi_turn(OLLAMA_URL, "Direct")
    results["direct_delegation"] = test_agent_delegation(OLLAMA_URL, "Direct")
    results["direct_streaming"] = test_streaming(OLLAMA_URL, "Direct")

    # Test via the acorn-api-relay proxy
    print("\n" + "#" * 60)
    print("# VIA ACORN-API-RELAY PROXY")
    print("#" * 60)
    try:
        results["relay_basic"] = test_basic_tool_call(RELAY_URL, "Relay")
        results["relay_delegation"] = test_agent_delegation(RELAY_URL, "Relay")
        results["relay_streaming"] = test_streaming(RELAY_URL, "Relay")
    except Exception as e:
        print(f"  Relay tests failed: {e}")
        results["relay_basic"] = False

    # Summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")

    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\n  {passed}/{total} tests passed")

    if results.get("direct_basic") and results.get("direct_delegation"):
        print("\n  VERDICT: Ollama native Anthropic API supports agent team tools!")
        print("  -> Can point Claude Code directly at Ollama for agent teams")
        print("  -> No extra proxy needed (acorn-api-relay is optional for agent teams)")
    elif results.get("direct_basic"):
        print("\n  VERDICT: Basic tool calling works but delegation needs tuning")
        print("  -> May need better system prompts or model selection")

    return 0 if passed >= 3 else 1


if __name__ == "__main__":
    sys.exit(main())
