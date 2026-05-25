"""Tests for configuration management."""

from content_engine.config.settings import Settings


def test_settings_defaults() -> None:
    """Settings should have sensible defaults."""
    settings = Settings(
        database_url="postgresql://test:test@localhost/test",
        openai_api_key="",
    )
    assert settings.app_env == "development"
    assert settings.log_level == "INFO"
    assert "postgresql" in settings.database_url


def test_settings_override() -> None:
    """Settings should accept overrides."""
    settings = Settings(
        database_url="postgresql://custom:custom@db:5432/custom",
        app_env="production",
        log_level="WARNING",
        openai_api_key="sk-test",
    )
    assert settings.app_env == "production"
    assert settings.log_level == "WARNING"
    assert settings.openai_api_key == "sk-test"
