from app.cli import main
from app.models import CEFRBand, Question, QuestionType
from app.storage import SQLiteOfflineQuestionRepository, SQLiteUserProgressRepository, SQLiteStorage
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
    assert "Offline question bank size: 0" in captured.out
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


def test_set_progress_can_jump_to_cefr_band(capsys, monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    monkeypatch.setenv("LUMINA_ROMANA_ENV", "test")
    monkeypatch.setenv("LUMINA_ROMANA_DATA_DIR", str(data_dir))

    exit_code = main(["set-progress", "--band", "B1"])
    captured = capsys.readouterr()

    storage = SQLiteStorage(data_dir / "lumina_romana.db")
    storage.initialize()
    repository = SQLiteUserProgressRepository(storage)
    progress = repository.get(DEFAULT_USER_ID)

    assert exit_code == 0
    assert "Set learner progress for default-learner." in captured.out
    assert "Current level: 7" in captured.out
    assert "Current CEFR band: B1" in captured.out
    assert progress is not None
    assert progress.current_level == 7
    assert progress.current_cefr_band.value == "B1"


def test_set_progress_can_jump_to_exact_level_with_difficulty_override(capsys, monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    monkeypatch.setenv("LUMINA_ROMANA_ENV", "test")
    monkeypatch.setenv("LUMINA_ROMANA_DATA_DIR", str(data_dir))

    exit_code = main(["set-progress", "--level", "9", "--difficulty", "10"])
    captured = capsys.readouterr()

    storage = SQLiteStorage(data_dir / "lumina_romana.db")
    storage.initialize()
    repository = SQLiteUserProgressRepository(storage)
    progress = repository.get(DEFAULT_USER_ID)

    assert exit_code == 0
    assert "Current level: 9" in captured.out
    assert "Current CEFR band: B2" in captured.out
    assert "Current difficulty: 10" in captured.out
    assert progress is not None
    assert progress.current_level == 9
    assert progress.current_difficulty == 10


def test_sample_content_runs_sampling_workflow(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("LUMINA_ROMANA_ENV", "test")
    monkeypatch.setenv("LUMINA_ROMANA_DATA_DIR", str(tmp_path / "data"))

    exit_code = main(["sample-content", "--topics", "romanian_basics", "b2_core_structures"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Lumina Romana content-quality sample" in captured.out
    assert "Samples run: 2" in captured.out
    assert "Metrics delta:" in captured.out
    assert "- romanian_basics:" in captured.out
    assert "- b2_core_structures:" in captured.out


def test_clear_offline_questions_empties_bank(capsys, monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    monkeypatch.setenv("LUMINA_ROMANA_ENV", "test")
    monkeypatch.setenv("LUMINA_ROMANA_DATA_DIR", str(data_dir))

    storage = SQLiteStorage(data_dir / "lumina_romana.db")
    storage.initialize()
    offline_repository = SQLiteOfflineQuestionRepository(storage)
    offline_repository.upsert_questions(
        "romanian_basics",
        [
            Question(
                question_id="q1",
                prompt="Choose the correct Romanian form of 'I am'.",
                question_type=QuestionType.MULTIPLE_CHOICE,
                difficulty_rating=2,
                cefr_band=CEFRBand.A1,
                correct_answer="sunt",
                explanation="'Eu sunt' means 'I am'.",
                tags=["romanian_basics", "a_fi_present"],
                options=["este", "sunt", "suntem", "esti"],
                hint="Match the form used with eu.",
            )
        ],
    )

    exit_code = main(["clear-offline-questions"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Cleared offline question bank." in captured.out
    assert offline_repository.count_all() == 0


def test_seed_offline_questions_populates_bank_for_requested_topics(capsys, monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    monkeypatch.setenv("LUMINA_ROMANA_ENV", "test")
    monkeypatch.setenv("LUMINA_ROMANA_DATA_DIR", str(data_dir))

    exit_code = main(["seed-offline-questions", "--topics", "romanian_basics", "b2_core_structures", "--question-count", "10"])
    captured = capsys.readouterr()

    storage = SQLiteStorage(data_dir / "lumina_romana.db")
    storage.initialize()
    offline_repository = SQLiteOfflineQuestionRepository(storage)

    assert exit_code == 0
    assert "Lumina Romana offline question bank seed" in captured.out
    assert "Topics processed: 2" in captured.out
    assert "- romanian_basics:" in captured.out
    assert "- b2_core_structures:" in captured.out
    assert offline_repository.count_for_topic("romanian_basics") >= 1
    assert offline_repository.count_for_topic("b2_core_structures") >= 1


def test_seed_offline_questions_defaults_to_100_per_topic(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("LUMINA_ROMANA_ENV", "test")
    monkeypatch.setenv("LUMINA_ROMANA_DATA_DIR", str(tmp_path / "data"))

    exit_code = main(["seed-offline-questions", "--topics", "romanian_basics"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "- romanian_basics:" in captured.out
    assert "requested minimum was 100" in captured.out


def test_seed_alias_runs_seed_offline_questions(capsys, monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    monkeypatch.setenv("LUMINA_ROMANA_ENV", "test")
    monkeypatch.setenv("LUMINA_ROMANA_DATA_DIR", str(data_dir))

    exit_code = main(["seed", "--topics", "romanian_basics", "--question-count", "10"])
    captured = capsys.readouterr()

    storage = SQLiteStorage(data_dir / "lumina_romana.db")
    storage.initialize()
    offline_repository = SQLiteOfflineQuestionRepository(storage)

    assert exit_code == 0
    assert "Lumina Romana offline question bank seed" in captured.out
    assert "- romanian_basics:" in captured.out
    assert offline_repository.count_for_topic("romanian_basics") >= 1


def test_serve_offline_flag_starts_server_in_offline_only_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("LUMINA_ROMANA_ENV", "test")
    monkeypatch.setenv("LUMINA_ROMANA_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LUMINA_ROMANA_AI_ENABLED", "true")
    monkeypatch.setenv("LUMINA_ROMANA_AI_PROVIDER", "gemini")
    monkeypatch.setenv("LUMINA_ROMANA_AI_MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("LUMINA_ROMANA_AI_API_KEY", "gemini-test-key")

    captured = {}

    def fake_run_dev_server(app):
        captured["offline_only"] = app.settings.ai.offline_only
        captured["provider_name"] = app.ai_service.provider.provider_name
        captured["configured"] = app.ai_service.is_configured

    monkeypatch.setattr("app.cli.run_dev_server", fake_run_dev_server)

    exit_code = main(["serve", "--offline"])

    assert exit_code == 0
    assert captured == {
        "offline_only": True,
        "provider_name": "offline",
        "configured": False,
    }


def test_serve_seed_flag_populates_bank_before_server_start(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("LUMINA_ROMANA_ENV", "test")
    monkeypatch.setenv("LUMINA_ROMANA_DATA_DIR", str(tmp_path / "data"))

    captured = {}

    def fake_run_dev_server(app):
        captured["romanian_basics_count"] = app.persistence.offline_questions.count_for_topic("romanian_basics")

    monkeypatch.setattr("app.cli.run_dev_server", fake_run_dev_server)

    exit_code = main(
        [
            "serve",
            "--seed-offline-questions",
            "--seed-topics",
            "romanian_basics",
            "--seed-question-count",
            "10",
        ]
    )
    captured_output = capsys.readouterr()

    assert exit_code == 0
    assert "Seeding offline question bank before starting web server." in captured_output.out
    assert "Lumina Romana offline question bank seed" in captured_output.out
    assert captured["romanian_basics_count"] >= 1


def test_top_level_offline_flag_defaults_to_serve(monkeypatch, tmp_path):
    monkeypatch.setenv("LUMINA_ROMANA_ENV", "test")
    monkeypatch.setenv("LUMINA_ROMANA_DATA_DIR", str(tmp_path / "data"))

    captured = {}

    def fake_run_dev_server(app):
        captured["offline_only"] = app.settings.ai.offline_only

    monkeypatch.setattr("app.cli.run_dev_server", fake_run_dev_server)

    exit_code = main(["-o"])

    assert exit_code == 0
    assert captured["offline_only"] is True
