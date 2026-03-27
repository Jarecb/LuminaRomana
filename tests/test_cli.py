from app.cli import main


def test_main_prints_startup_message(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("LUMINA_ROMANA_ENV", "test")
    monkeypatch.setenv("LUMINA_ROMANA_DATA_DIR", str(tmp_path / "data"))

    exit_code = main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Lumina Romana is ready." in captured.out
    assert "Environment: test" in captured.out
    assert "Database path:" in captured.out
    assert "Seed topics loaded: 6" in captured.out
