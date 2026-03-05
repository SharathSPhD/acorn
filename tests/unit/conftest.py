"""Unit test configuration — disables CORTEX+ autostart to prevent background DB calls."""
import pytest


@pytest.fixture(autouse=True)
def disable_cortex_autostart(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable CORTEX+ autostart for all unit tests.

    CORTEX+ starts asyncpg background tasks in the lifespan. Unit tests mock asyncpg
    with limited side_effects and cannot anticipate CORTEX+ DB calls. Disable it here
    so TestClient(app) does not trigger the cognitive loop.
    """
    import api.main as _main_mod
    monkeypatch.setattr(_main_mod.settings, "cortex_autostart", False)
