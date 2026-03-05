#!/usr/bin/env python3
"""
acorn-session: Session state manager for ACORN harness containers.
Saves/restores five state categories to Redis so agent context
survives container restarts (PRD §5.3: session recovery requirement).

Usage:
    acorn-session save    -- called by post-tool-use.sh
    acorn-session restore -- called at container startup
"""
__pattern__ = "Repository"

import sys
import os
import json
import subprocess
import redis

def get_redis():
    url = os.environ.get("REDIS_URL", "redis://acorn-redis:6379")
    return redis.from_url(url, decode_responses=True)

def get_ttl():
    return int(os.environ.get("ACORN_SESSION_TTL_HOURS", "24")) * 3600

def agent_key(category: str) -> str:
    agent_id = os.environ.get("ACORN_AGENT_ID", "unknown")
    return f"acorn:session:{agent_id}:{category}"

def save_session():
    r = get_redis()
    ttl = get_ttl()

    # 1. Current working directory
    r.setex(agent_key("cwd"), ttl, os.getcwd())

    # 2. Git state (branch + last commit)
    try:
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"], text=True).strip()
        commit = subprocess.check_output(
            ["git", "log", "-1", "--oneline"], text=True).strip()
        r.setex(agent_key("git"), ttl, json.dumps({"branch": branch, "commit": commit}))
    except Exception:
        pass

    # 3. Environment variables (ACORN-specific only)
    acorn_env = {k: v for k, v in os.environ.items() if k.startswith("ACORN_") or k.startswith("PROBLEM_")}
    r.setex(agent_key("env"), ttl, json.dumps(acorn_env))

    # 4. Open files (tracked via /tmp/acorn-open-files.json if exists)
    open_files_path = "/tmp/acorn-open-files.json"
    if os.path.exists(open_files_path):
        r.setex(agent_key("open_files"), ttl, open(open_files_path).read())

    print(f"[acorn-session] Saved session for {os.environ.get('ACORN_AGENT_ID', 'unknown')}")

def restore_session():
    r = get_redis()
    agent_id = os.environ.get("ACORN_AGENT_ID", "unknown")

    # 1. Restore CWD
    cwd = r.get(agent_key("cwd"))
    if cwd and os.path.isdir(cwd):
        os.chdir(cwd)
        print(f"[acorn-session] Restored cwd: {cwd}")

    # 2. Restore git state (informational — git checkout is not done automatically)
    git_state = r.get(agent_key("git"))
    if git_state:
        state = json.loads(git_state)
        print(f"[acorn-session] Last git state: branch={state.get('branch')}, commit={state.get('commit')}")

    # 3. Restore env vars
    env_state = r.get(agent_key("env"))
    if env_state:
        env = json.loads(env_state)
        for k, v in env.items():
            os.environ[k] = v

    print(f"[acorn-session] Session restored for {agent_id}")

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("save", "restore"):
        print("Usage: acorn-session save|restore", file=sys.stderr)
        sys.exit(1)
    if sys.argv[1] == "save":
        save_session()
    else:
        restore_session()
