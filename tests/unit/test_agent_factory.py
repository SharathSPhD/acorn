"""Unit tests for AgentFactory implementations."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.config import AcornSettings
from api.factories.agent_factory import (
    AgentSpec,
    DGXAgentFactory,
    ResourceCapExceededError,
    get_agent_factory,
)


def _mock_subprocess(returncode: int = 0, stdout: bytes = b"abc123\n", stderr: bytes = b""):
    """Create a mock for asyncio.create_subprocess_exec."""
    mock_proc = AsyncMock()
    mock_proc.returncode = returncode
    mock_proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return mock_proc


def test_agent_factory__create__returns_valid_spec():
    spec = DGXAgentFactory().create("data-engineer", "prob-001")
    assert isinstance(spec, AgentSpec)
    assert spec.role == "data-engineer"
    assert spec.problem_uuid == "prob-001"
    assert spec.harness_image == "acorn/harness:latest"
    assert spec.agent_id


def test_agent_factory__create__generates_unique_agent_ids():
    f = DGXAgentFactory()
    assert f.create("de", "p").agent_id != f.create("de", "p").agent_id


def test_agent_factory__create__uses_model_for_role():
    s = AcornSettings()
    spec = DGXAgentFactory().create("data-scientist", "p1")
    assert spec.model == s.analysis_model


def test_agent_factory__create__accepts_container_name_kwarg():
    spec = DGXAgentFactory().create("de", "p", container_name="my-container")
    assert spec.agent_id == "my-container"


def test_agent_factory__create__accepts_task_id_kwarg():
    spec = DGXAgentFactory().create("de", "p", task_id="task-abc")
    assert spec.task_id == "task-abc"


@pytest.mark.asyncio
async def test_agent_factory__launch__returns_container_id():
    spec = DGXAgentFactory().create("ds", "prob-123")
    mock_proc = _mock_subprocess(stdout=b"abc123container\n")
    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        result = await DGXAgentFactory().launch(spec)
    assert result == "abc123container"


@pytest.mark.asyncio
async def test_agent_factory__launch__raises_on_docker_failure():
    spec = DGXAgentFactory().create("de", "p")
    mock_proc = _mock_subprocess(returncode=1, stderr=b"No such image")
    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with pytest.raises(ResourceCapExceededError, match="No such image"):
            await DGXAgentFactory().launch(spec)


@pytest.mark.asyncio
async def test_agent_factory__launch__passes_env_vars():
    spec = DGXAgentFactory().create("ds", "prob-123")
    spec.model = "glm-4.7"
    mock_proc = _mock_subprocess()
    with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
        await DGXAgentFactory().launch(spec)
    cmd = mock_exec.call_args[0]
    cmd_str = " ".join(str(a) for a in cmd)
    assert "ACORN_MODEL=glm-4.7" in cmd_str
    assert "ACORN_ROLE=ds" in cmd_str
    assert "ANTHROPIC_BASE_URL=" in cmd_str


@pytest.mark.asyncio
async def test_agent_factory__launch__includes_network_and_volume():
    spec = DGXAgentFactory().create("de", "p")
    spec.network = "test-net"
    spec.workspace_path = "/tmp/workspace"
    mock_proc = _mock_subprocess()
    with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
        await DGXAgentFactory().launch(spec)
    cmd = mock_exec.call_args[0]
    cmd_str = " ".join(str(a) for a in cmd)
    assert "--network test-net" in cmd_str
    assert "/tmp/workspace:/workspace" in cmd_str


@pytest.mark.asyncio
async def test_agent_factory__launch__includes_task_id_env():
    spec = DGXAgentFactory().create("de", "p", task_id="tid-99")
    mock_proc = _mock_subprocess()
    with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
        await DGXAgentFactory().launch(spec)
    cmd_str = " ".join(str(a) for a in mock_exec.call_args[0])
    assert "ACORN_TASK_ID=tid-99" in cmd_str


def test_agent_factory__get_agent_factory__returns_dgx_by_default():
    factory = get_agent_factory()
    assert isinstance(factory, DGXAgentFactory)


def test_config__model_for_role__coder_roles():
    s = AcornSettings()
    assert s.model_for_role("data-engineer") == s.coder_model
    assert s.model_for_role("ml-engineer") == s.coder_model


def test_config__model_for_role__analysis_roles():
    s = AcornSettings()
    assert s.model_for_role("data-scientist") == s.analysis_model
    assert s.model_for_role("kernel-extractor") == s.analysis_model


def test_config__model_for_role__reasoning_roles():
    s = AcornSettings()
    assert s.model_for_role("meta-agent") == s.reasoning_model
    assert s.model_for_role("software-architect") == s.reasoning_model
