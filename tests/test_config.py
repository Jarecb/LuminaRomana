from app.bootstrap import create_application
from app.config import Settings


def test_settings_load_from_environment(monkeypatch):
    monkeypatch.setenv("LUMINA_ROMANA_ENV", "test")
    monkeypatch.setenv("LUMINA_ROMANA_LOG_LEVEL", "debug")
    monkeypatch.setenv("LUMINA_ROMANA_DATA_DIR", "tmp-data")
    monkeypatch.setenv("LUMINA_ROMANA_AI_ENABLED", "true")
    monkeypatch.setenv("LUMINA_ROMANA_AI_PROVIDER", "openai")
    monkeypatch.setenv("LUMINA_ROMANA_AI_MODEL", "gpt-4.1-mini")
    monkeypatch.setenv("LUMINA_ROMANA_AI_API_KEY", "test-key")
    monkeypatch.setenv("LUMINA_ROMANA_AI_BASE_URL", "https://example.test/v1/")
    monkeypatch.setenv("LUMINA_ROMANA_AI_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("LUMINA_ROMANA_AI_MAX_RETRIES", "4")
    monkeypatch.setenv("LUMINA_ROMANA_WEB_HOST", "0.0.0.0")
    monkeypatch.setenv("LUMINA_ROMANA_WEB_PORT", "9001")
    monkeypatch.delenv("LUMINA_ROMANA_DB_PATH", raising=False)

    settings = Settings.load()

    assert settings.environment == "test"
    assert settings.log_level == "DEBUG"
    assert str(settings.data_dir) == "tmp-data"
    assert str(settings.database_path) == "tmp-data\\lumina_romana.db"
    assert settings.ai.enabled is True
    assert settings.ai.provider == "openai"
    assert settings.ai.model == "gpt-4.1-mini"
    assert settings.ai.api_key == "test-key"
    assert settings.ai.base_url == "https://example.test/v1"
    assert settings.ai.timeout_seconds == 12.5
    assert settings.ai.max_retries == 4
    assert settings.ai.configured is True
    assert settings.web.host == "0.0.0.0"
    assert settings.web.port == 9001


def test_create_application_uses_loaded_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("LUMINA_ROMANA_ENV", "test")
    monkeypatch.setenv("LUMINA_ROMANA_DATA_DIR", str(tmp_path / "runtime"))

    app = create_application()

    assert app.settings.app_name == "Lumina Romana"
    assert app.settings.environment == "test"
    assert app.logger.name == "lumina_romana"
    assert app.settings.database_path.exists()
    assert len(app.content_library.all_topics()) == 10
    assert app.ai_service.is_configured is False
    assert app.ai_service.provider.provider_name == "disabled"
    assert app.learning_service is not None
