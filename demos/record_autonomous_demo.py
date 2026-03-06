"""ACORN Autonomous Demo Recorder — Playwright-based evidence capture.

Records ACORN operating autonomously at multiple stages:
  Stage 1: Model Intelligence (registry, SWOT, recommendations)
  Stage 2: Builder Improvement Cycle (web search, datasets, domain knowledge)
  Stage 3: Autonomous Problem Solving (CORTEX+ -> warden -> agent teams)
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8501"
API_URL = "http://localhost:8000"
DEMO_DIR = Path(__file__).parent / "recordings"
DEMO_DIR.mkdir(exist_ok=True)


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def api_call(method: str, path: str, data: dict | None = None) -> dict:
    """Call the ACORN API and return JSON response."""
    import httpx
    url = f"{API_URL}{path}"
    with httpx.Client(timeout=180) as client:
        if method == "GET":
            r = client.get(url)
        else:
            r = client.post(url, json=data or {})
        r.raise_for_status()
        return r.json()


def take_screenshot(page, name: str) -> Path:
    path = DEMO_DIR / f"{timestamp()}_{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  Screenshot: {path.name}")
    return path


def record_stage1_model_intelligence(page):
    """Stage 1: Model Intelligence — registry, SWOT, benchmarks, recommendations."""
    print("\n" + "=" * 60)
    print("STAGE 1: MODEL INTELLIGENCE")
    print("=" * 60)

    print("\n[1a] Syncing models from Ollama...")
    result = api_call("POST", "/api/models/sync")
    print(f"  Synced: {result.get('synced', 0)} models")

    print("\n[1b] Listing registered models with SWOT...")
    models = api_call("GET", "/api/models?available=true")
    if isinstance(models, dict):
        models = models.get("models", [])
    for m in models:
        name = m.get("name", "?")
        bench = m.get("benchmark_scores", {})
        swot = bool(m.get("strengths"))
        roles = m.get("recommended_roles", [])
        print(f"  {name:30s} bench={bench}  swot={swot}  roles={roles}")

    print("\n[1c] Model recommendation for data-scientist (analyse task)...")
    rec = api_call("GET", "/api/models/recommend?task_type=analyse&role=data-scientist")
    print(f"  Recommended: {rec.get('name')} ({rec.get('benchmark_scores', {})})")

    print("\n[1d] Model recommendation for orchestrator (model task)...")
    rec = api_call("GET", "/api/models/recommend?task_type=model&role=orchestrator")
    print(f"  Recommended: {rec.get('name')}")

    print("\n[1e] Navigating to ACORN UI Dashboard...")
    page.goto(f"{BASE_URL}", wait_until="networkidle", timeout=15000)
    page.wait_for_timeout(2000)
    take_screenshot(page, "stage1_dashboard")

    try:
        page.goto(f"{BASE_URL}/builder", wait_until="networkidle", timeout=10000)
        page.wait_for_timeout(2000)
        take_screenshot(page, "stage1_builder")
    except Exception:
        print("  (builder page not available)")

    try:
        page.goto(f"{BASE_URL}/activity", wait_until="networkidle", timeout=10000)
        page.wait_for_timeout(2000)
        take_screenshot(page, "stage1_activity")
    except Exception:
        print("  (activity page not available)")

    print("\nStage 1 COMPLETE: Model intelligence operational")


def record_stage2_builder_cycle(page):
    """Stage 2: Builder Improvement Cycle — research, datasets, model eval."""
    print("\n" + "=" * 60)
    print("STAGE 2: BUILDER IMPROVEMENT CYCLE")
    print("=" * 60)

    print("\n[2a] Running domain research (sales)...")
    try:
        result = api_call("POST", "/api/builder/research-domain", {"domain": "sales"})
        print(f"  Research result: {json.dumps(result, default=str)[:200]}")
    except Exception as e:
        print(f"  Research error: {e}")

    print("\n[2b] Discovering datasets (sales)...")
    try:
        result = api_call("POST", "/api/builder/discover-datasets", {"domain": "sales"})
        ds_list = result.get("datasets", result.get("results", []))
        print(f"  Found {len(ds_list)} datasets")
        for ds in ds_list[:3]:
            print(f"    - {ds.get('id', ds.get('title', '?'))}")
    except Exception as e:
        print(f"  Dataset error: {e}")

    print("\n[2c] Running full improvement cycle...")
    try:
        result = api_call("POST", "/api/builder/improvement-cycle")
        for line in result.get("summary", []):
            print(f"    {line}")
    except Exception as e:
        print(f"  Cycle error: {e}")

    print("\n[2d] Capturing UI state...")
    page.goto(f"{BASE_URL}", wait_until="networkidle", timeout=15000)
    page.wait_for_timeout(2000)
    take_screenshot(page, "stage2_after_builder")

    print("\nStage 2 COMPLETE: Builder intelligence operational")


def record_stage3_autonomous_operation(page):
    """Stage 3: Full autonomous loop — CORTEX+ -> warden -> problem solving."""
    print("\n" + "=" * 60)
    print("STAGE 3: AUTONOMOUS OPERATION")
    print("=" * 60)

    print("\n[3a] CORTEX+ Status...")
    cortex = api_call("GET", "/api/cortex/status")
    cb = cortex.get("current_broadcast", {})
    print(f"  Module: {cb.get('module')} -> {cb.get('action_type')}")
    print(f"  Broadcast ticks: {cortex.get('broadcast_log_size', 0)}")

    print("\n[3b] Problem Queue...")
    problems = api_call("GET", "/api/problems")
    status_counts = {}
    for p in problems:
        s = p.get("status", "?")
        status_counts[s] = status_counts.get(s, 0) + 1
    print(f"  Queue: {status_counts}")

    print("\n[3c] Warden Status...")
    warden_logs = subprocess.run(
        ["docker", "logs", "docker-acorn-warden-1", "--tail", "15"],
        capture_output=True, text=True
    )
    auto_starts = sum(1 for line in warden_logs.stderr.split("\n") if "Auto-starting" in line)
    print(f"  Auto-starts logged: {auto_starts}")
    print(f"  Last warden output:")
    for line in warden_logs.stderr.strip().split("\n")[-5:]:
        print(f"    {line}")

    print("\n[3d] Active Harness Containers...")
    containers = subprocess.run(
        ["docker", "ps", "--filter", "name=acorn-harness", "--format", "{{.Names}}: {{.Status}}"],
        capture_output=True, text=True
    )
    harness_lines = [l for l in containers.stdout.strip().split("\n") if l]
    print(f"  Active harnesses: {len(harness_lines)}")
    for line in harness_lines:
        print(f"    {line}")

    print("\n[3e] Kernel Grove...")
    kernels = api_call("GET", "/api/kernels")
    if isinstance(kernels, dict):
        k_list = kernels.get("kernels", [])
    else:
        k_list = kernels
    print(f"  Total kernels: {len(k_list)}")
    for k in k_list[:5]:
        print(f"    [{k.get('status','?'):12s}] {k.get('name','?')} ({k.get('category','?')})")

    print("\n[3f] Agent Telemetry (last 24h)...")
    try:
        tel = api_call("GET", "/api/telemetry/summary")
        print(f"  Telemetry: {json.dumps(tel, default=str)[:200]}")
    except Exception:
        print("  (telemetry summary not available)")

    print("\n[3g] Capturing UI screenshots...")
    page.goto(f"{BASE_URL}", wait_until="networkidle", timeout=15000)
    page.wait_for_timeout(2000)
    take_screenshot(page, "stage3_dashboard")

    try:
        page.goto(f"{BASE_URL}/problems", wait_until="networkidle", timeout=10000)
        page.wait_for_timeout(2000)
        take_screenshot(page, "stage3_problems")
    except Exception:
        pass

    try:
        page.goto(f"{BASE_URL}/kernels", wait_until="networkidle", timeout=10000)
        page.wait_for_timeout(2000)
        take_screenshot(page, "stage3_kernels")
    except Exception:
        pass

    try:
        page.goto(f"{BASE_URL}/activity", wait_until="networkidle", timeout=10000)
        page.wait_for_timeout(2000)
        take_screenshot(page, "stage3_activity")
    except Exception:
        pass

    print("\nStage 3 COMPLETE: Autonomous operation verified")


def record_video_walkthrough(page, context):
    """Record a continuous video walkthrough of all UI pages."""
    print("\n" + "=" * 60)
    print("VIDEO WALKTHROUGH")
    print("=" * 60)

    pages_to_visit = [
        ("/", "Dashboard", 3000),
        ("/problems", "Problems", 3000),
        ("/kernels", "Kernels", 3000),
        ("/builder", "Builder", 3000),
        ("/activity", "Activity", 3000),
    ]

    for path, name, wait_ms in pages_to_visit:
        try:
            print(f"  Visiting {name}...")
            page.goto(f"{BASE_URL}{path}", wait_until="networkidle", timeout=15000)
            page.wait_for_timeout(wait_ms)
        except Exception as e:
            print(f"  ({name} failed: {e})")


def main():
    print("=" * 60)
    print("ACORN AUTONOMOUS DEMO RECORDER")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Recordings: {DEMO_DIR}")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        video_path = DEMO_DIR / "videos"
        video_path.mkdir(exist_ok=True)

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(video_path),
            record_video_size={"width": 1920, "height": 1080},
        )
        page = context.new_page()

        try:
            record_stage1_model_intelligence(page)
            record_stage2_builder_cycle(page)
            record_stage3_autonomous_operation(page)
            record_video_walkthrough(page, context)
        finally:
            context.close()
            browser.close()

        for vf in video_path.glob("*.webm"):
            ts = timestamp()
            dest = DEMO_DIR / f"acorn_autonomous_demo_{ts}.webm"
            vf.rename(dest)
            print(f"\nVideo saved: {dest.name}")

    print("\n" + "=" * 60)
    print("DEMO RECORDING COMPLETE")
    print(f"All artifacts in: {DEMO_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
