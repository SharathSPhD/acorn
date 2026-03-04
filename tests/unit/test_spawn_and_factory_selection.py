"""Tests for factory selection logic and spawn models."""
from unittest.mock import patch

from api.factories.agent_factory import (
    CloudAgentFactory,
    DGXAgentFactory,
    MiniAgentFactory,
    get_agent_factory,
)
from api.models import SpawnAgentRequest


def test_spawn_agent_request__defaults():
    req = SpawnAgentRequest(role="data-engineer")
    assert req.role == "data-engineer"
    assert req.task_id is None


def test_spawn_agent_request__with_task_id():
    req = SpawnAgentRequest(role="judge", task_id="abc-123")
    assert req.task_id == "abc-123"


def test_get_agent_factory__dgx_default():
    factory = get_agent_factory()
    assert isinstance(factory, DGXAgentFactory)


def test_get_agent_factory__mini_mode():
    with patch("api.factories.agent_factory.settings") as mock_settings:
        mock_settings.oak_mode = "mini"
        factory = get_agent_factory()
    assert isinstance(factory, MiniAgentFactory)


def test_get_agent_factory__cloud_mode():
    with patch("api.factories.agent_factory.settings") as mock_settings:
        mock_settings.oak_mode = "cloud"
        factory = get_agent_factory()
    assert isinstance(factory, CloudAgentFactory)
