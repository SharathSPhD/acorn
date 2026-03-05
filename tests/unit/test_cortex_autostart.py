"""Unit tests for CORTEX+ autostart and reconciliation configuration."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from api.config import AcornSettings


def test_cortex_autostart__default__is_true():
    """cortex_autostart defaults to True so CORTEX+ self-starts on API boot."""
    settings = AcornSettings()
    assert settings.cortex_autostart is True


def test_cortex_enabled__default__is_false():
    """cortex_enabled defaults to False (legacy flag; autostart is the new gate)."""
    settings = AcornSettings()
    assert settings.cortex_enabled is False


def test_cortex_reconcile_interval__default__is_300():
    """cortex_reconcile_interval defaults to 300 seconds (5-minute reconcile)."""
    settings = AcornSettings()
    assert settings.cortex_reconcile_interval == 300


def test_meta_agent_schedule_problems__default__is_10():
    """meta_agent_schedule_problems defaults to 10 (trigger after every 10 completions)."""
    settings = AcornSettings()
    assert settings.meta_agent_schedule_problems == 10


@pytest.mark.asyncio
async def test_cortex_autostart__lifespan__starts_cortex_when_true():
    """Lifespan starts CORTEX+ cognitive loop when cortex_autostart=True."""
    mock_cortex = MagicMock()
    mock_task = AsyncMock()
    mock_cortex.run = AsyncMock(return_value=None)

    with patch("api.main.settings") as mock_settings, \
         patch("api.main.get_event_bus") as mock_bus, \
         patch("api.services.cortex.get_cortex", return_value=mock_cortex), \
         patch("asyncio.create_task", return_value=mock_task):

        mock_settings.cortex_autostart = True

        from api.main import lifespan
        from fastapi import FastAPI
        app = FastAPI()

        async with lifespan(app):
            pass

        mock_bus.assert_called_once()


@pytest.mark.asyncio
async def test_cortex_autostart__lifespan__skips_cortex_when_false():
    """Lifespan does NOT start CORTEX+ when cortex_autostart=False."""
    with patch("api.main.settings") as mock_settings, \
         patch("api.main.get_event_bus"), \
         patch("asyncio.create_task") as mock_no_task:

        mock_settings.cortex_autostart = False

        from api.main import lifespan
        from fastapi import FastAPI
        app = FastAPI()

        async with lifespan(app):
            pass

        mock_no_task.assert_not_called()


def test_cortex_plus__tick_interval__uses_config():
    """CortexPlus reads tick_interval from settings."""
    with patch("api.services.cortex.settings") as mock_settings:
        mock_settings.cortex_tick_interval = 60
        mock_settings.database_url = "postgresql://acorn:acorn@localhost:5432/acorn"

        from api.services.cortex import CortexPlus
        cortex = CortexPlus()
        assert cortex.tick_interval == 60


def test_cortex_plus__initial_state__not_running():
    """CortexPlus starts in stopped state."""
    from api.services.cortex import CortexPlus
    cortex = CortexPlus()
    assert cortex.running is False
    assert cortex.current_broadcast is None
    assert len(cortex.broadcast_log) == 0


def test_cortex_plus__get_status__returns_structured_dict():
    """get_status returns dict with running, tick_interval, broadcast_log_size."""
    from api.services.cortex import CortexPlus
    cortex = CortexPlus()
    status = cortex.get_status()
    assert "running" in status
    assert "tick_interval" in status
    assert "broadcast_log_size" in status
    assert status["running"] is False
    assert status["current_broadcast"] is None
