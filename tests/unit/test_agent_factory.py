"""Unit tests for AgentFactory implementations."""
import pytest
from unittest.mock import patch, MagicMock
from api.factories.agent_factory import DGXAgentFactory, AgentSpec, ResourceCapExceededError
from api.config import OAKSettings


@pytest.fixture
def mock_docker():
    mock_result = MagicMock(returncode=0, stdout="abc123container\n")
    with patch("subprocess.run", return_value=mock_result) as m:
        yield m


def test_agent_factory__create__returns_valid_spec():
    spec = DGXAgentFactory().create("data-engineer", "prob-001")
    assert isinstance(spec, AgentSpec)
    assert spec.role == "data-engineer"
    assert spec.problem_uuid == "prob-001"
    assert spec.harness_image == "oak/harness:latest"
    assert spec.agent_id


def test_agent_factory__create__generates_unique_agent_ids():
    f = DGXAgentFactory()
    assert f.create("de", "p").agent_id != f.create("de", "p").agent_id


def test_agent_factory__launch__calls_docker_run(mock_docker):
    spec = DGXAgentFactory().create("ds", "prob-123")
    container_id = DGXAgentFactory().launch(spec)
    assert container_id == "abc123container"
    cmd = mock_docker.call_args[0][0]
    assert "docker" in cmd and "run" in cmd and "-d" in cmd


def test_agent_factory__launch__returns_container_id():
    spec = DGXAgentFactory().create("ds", "prob-123")
    mock_result = MagicMock(returncode=0, stdout="abc123\n")
    with patch("subprocess.run", return_value=mock_result):
        assert DGXAgentFactory().launch(spec) == "abc123"


def test_agent_factory__launch__raises_on_docker_failure():
    spec = DGXAgentFactory().create("de", "p")
    mock_result = MagicMock(returncode=1, stderr="No such image")
    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(ResourceCapExceededError):
            DGXAgentFactory().launch(spec)


def test_agent_factory__launch__passes_model_env_var(mock_docker):
    spec = DGXAgentFactory().create("ds", "prob-123")
    spec.model = "glm-4.7"
    DGXAgentFactory().launch(spec)
    cmd = mock_docker.call_args[0][0]
    assert "OAK_MODEL=glm-4.7" in cmd


def test_config__model_for_role__coder_roles():
    s = OAKSettings()
    assert s.model_for_role("data-engineer") == s.coder_model
    assert s.model_for_role("ml-engineer") == s.coder_model


def test_config__model_for_role__analysis_roles():
    s = OAKSettings()
    assert s.model_for_role("data-scientist") == s.analysis_model
    assert s.model_for_role("skill-extractor") == s.analysis_model


def test_config__model_for_role__reasoning_roles():
    s = OAKSettings()
    assert s.model_for_role("orchestrator") == s.reasoning_model
    assert s.model_for_role("judge-agent") == s.reasoning_model
