from app.cli import main
from app.storage import SQLiteUserProgressRepository, SQLiteStorage
from app.services.learning import DEFAULT_USER_ID


def test_main_prints_startup_message(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("LUMINA_ROMANA_ENV", "test")
    monkeypatch.setenv("LUMINA_ROMANA_DATA_DIR", str(tmp_path / "data"))

    exit_code = main([])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Lumina Romana developer status" in captured.out
    assert "Environment: test" in captured.out
    assert "Database path:" in captured.out
    assert "Seed topics loaded: 10" in captured.out
    assert "AI provider: disabled" in captured.out
    assert "Web UI: http://127.0.0.1:8000" in captured.out
    assert "Run `python main.py serve`" in captured.out


def test_reset_progress_clears_default_learner(capsys, monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    monkeypatch.setenv("LUMINA_ROMANA_ENV", "test")
    monkeypatch.setenv("LUMINA_ROMANA_DATA_DIR", str(data_dir))

    storage = SQLiteStorage(data_dir / "lumina_romana.db")
    storage.initialize()
    repository = SQLiteUserProgressRepository(storage)
    from app.models import UserProgress

    seeded = UserProgress(user_id=DEFAULT_USER_ID, current_level=4, current_difficulty=5, total_xp=220)
    repository.save(seeded)

    exit_code = main(["reset-progress"])
    captured = capsys.readouterr()
    reset_progress = repository.get(DEFAULT_USER_ID)

    assert exit_code == 0
    assert "Reset learner progress for default-learner." in captured.out
    assert reset_progress is not None
    assert reset_progress.current_level == 1
    assert reset_progress.current_difficulty == 1
    assert reset_progress.total_xp == 0
