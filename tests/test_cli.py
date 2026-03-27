from app.cli import main


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
