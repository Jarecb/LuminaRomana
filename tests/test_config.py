from app.bootstrap import create_application
from app.config import Settings


def test_settings_load_from_environment(monkeypatch):
    monkeypatch.setenv("LUMINA_ROMANA_ENV", "test")
    monkeypatch.setenv("LUMINA_ROMANA_LOG_LEVEL", "debug")
    monkeypatch.setenv("LUMINA_ROMANA_DATA_DIR", "tmp-data")
    monkeypatch.delenv("LUMINA_ROMANA_DB_PATH", raising=False)

    settings = Settings.load()

    assert settings.environment == "test"
    assert settings.log_level == "DEBUG"
    assert str(settings.data_dir) == "tmp-data"
    assert str(settings.database_path) == "tmp-data\\lumina_romana.db"


def test_create_application_uses_loaded_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("LUMINA_ROMANA_ENV", "test")
    monkeypatch.setenv("LUMINA_ROMANA_DATA_DIR", str(tmp_path / "runtime"))

    app = create_application()

    assert app.settings.app_name == "Lumina Romana"
    assert app.settings.environment == "test"
    assert app.logger.name == "lumina_romana"
    assert app.settings.database_path.exists()
    assert len(app.content_library.all_topics()) == 6
