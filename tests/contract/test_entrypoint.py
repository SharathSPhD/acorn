"""Contract tests for docker/claude-harness/scripts/entrypoint.sh.

Verifies that the harness entrypoint correctly constructs the initial prompt
and that it does NOT wrap claude with tool-proxy (which would silently swallow it).
"""
import pathlib
import re

ENTRYPOINT = (
    pathlib.Path(__file__).parent.parent.parent
    / "docker" / "claude-harness" / "scripts" / "entrypoint.sh"
)


def _script() -> str:
    return ENTRYPOINT.read_text()


def test_entrypoint__exists():
    assert ENTRYPOINT.exists(), "entrypoint.sh must exist"


def test_entrypoint__invokes_claude_directly__not_via_tool_proxy():
    """tool-proxy is a check-and-exit hook; entrypoint must call claude directly."""
    script = _script()
    # Must NOT use tool-proxy as a wrapper for claude
    assert "exec tool-proxy claude" not in script, (
        "entrypoint.sh must not call 'exec tool-proxy claude' — "
        "tool-proxy is a deny-list checker (exits 0/2), not a command wrapper. "
        "Claude Code would never be started."
    )


def test_entrypoint__calls_claude_with_dangerously_skip_permissions():
    script = _script()
    assert "claude --dangerously-skip-permissions" in script


def test_entrypoint__passes_initial_prompt_with_p_flag():
    script = _script()
    assert re.search(r"claude.*-p.*INITIAL_PROMPT", script), (
        "claude must be invoked with -p $INITIAL_PROMPT for non-interactive mode"
    )


def test_entrypoint__exits_on_missing_problem_uuid():
    """Entrypoint must guard against missing OAK_PROBLEM_UUID."""
    script = _script()
    assert "OAK_PROBLEM_UUID" in script
    assert "exit 1" in script


def test_entrypoint__constructs_initial_prompt_from_problem_json():
    script = _script()
    assert "TITLE" in script
    assert "DESCRIPTION" in script
    assert "INITIAL_PROMPT" in script
