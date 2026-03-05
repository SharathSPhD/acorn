"""Unit tests for AcornSettings configuration."""
from api.config import AcornSettings


def test_config__default_mode__is_dgx():
    settings = AcornSettings()
    assert settings.acorn_mode == "dgx"


def test_config__judge_required__defaults_true():
    settings = AcornSettings()
    assert settings.judge_required is True


def test_config__database_url__contains_postgresql():
    settings = AcornSettings()
    assert "postgresql" in settings.database_url


def test_config__settings_is_singleton__same_object():
    from api.config import settings as s1
    from api.config import settings as s2
    assert s1 is s2
