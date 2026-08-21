import sys
from unittest.mock import MagicMock, patch

from models import Message


def test_cli_check_command_with_key(monkeypatch, tmp_path, capsys):
    test_db = str(tmp_path / "test_mem.db")
    monkeypatch.setattr(sys, "argv", ["main.py", "check"])
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
    
    # We patch Path since the db is at Path(config.data_dir)/"memory"/"memory.db" 
    # But wait, config.data_dir uses expanduser so patching expanduser works for config loading
    monkeypatch.setattr("os.path.expanduser", lambda p: str(tmp_path) if "~" in p else p)

    from main import main
    main()

    captured = capsys.readouterr().out
    assert "Checking Configuration..." in captured
    assert "OpenAI Key: Present" in captured
    assert "Checking Database..." in captured
    assert "Database OK" in captured


def test_cli_check_command_without_key(monkeypatch, tmp_path, capsys):
    test_db = str(tmp_path / "test_mem.db")
    monkeypatch.setattr(sys, "argv", ["main.py", "check"])
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("os.path.expanduser", lambda p: str(tmp_path) if "~" in p else p)

    from main import main
    main()

    captured = capsys.readouterr().out
    assert "Checking Configuration..." in captured
    assert "OpenAI Key: Present" not in captured
    assert "Checking Database..." in captured
    assert "Database OK" in captured


def test_cli_memory_demo(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sys, "argv", ["main.py", "memory", "--demo"])
    monkeypatch.setattr("os.path.expanduser", lambda p: str(tmp_path) if "~" in p else p)

    from main import main
    main()

    captured = capsys.readouterr().out
    assert "Relevant Context:" in captured
    assert "The user loves Python and SQLite." in captured


def test_cli_missing_api_key(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sys, "argv", ["main.py"])
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("os.path.expanduser", lambda p: str(tmp_path) if "~" in p else p)

    from main import main
    main()

    captured = capsys.readouterr().out
    assert "Error: OPENAI_API_KEY must be set when using openai provider" in captured


def test_cli_interactive_loop(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sys, "argv", ["main.py", "chat"])
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
    monkeypatch.setattr("os.path.expanduser", lambda p: str(tmp_path) if "~" in p else p)

    user_inputs = iter(["Hello AI", "/quit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(user_inputs))

    mock_agent_instance = MagicMock()
    mock_agent_instance.run.return_value = [
        Message(role="system", content="You are a helpful AI."),
        Message(role="user", content="Hello AI"),
        Message(role="assistant", content="Hello! How can I help you today?"),
    ]

    with patch("cli.repl.Agent", return_value=mock_agent_instance) as mock_agent_cls, \
         patch("cli.repl.create_provider") as mock_provider_cls:
        from main import main
        main()

        assert mock_agent_cls.called
        assert mock_provider_cls.called
        mock_agent_instance.run.assert_called_once()

    captured = capsys.readouterr().out
    assert "Pygent started. Type /quit to exit." in captured
    assert "AI: Hello! How can I help you today?" in captured


def test_cli_interactive_loop_eof(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sys, "argv", ["main.py", "chat"])
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
    monkeypatch.setattr("os.path.expanduser", lambda p: str(tmp_path) if "~" in p else p)

    def raise_eof(prompt=""):
        raise EOFError()

    monkeypatch.setattr("builtins.input", raise_eof)

    with patch("cli.repl.Agent"), patch("cli.repl.create_provider"):
        from main import main
        main()

    captured = capsys.readouterr().out
    assert "Pygent started. Type /quit to exit." in captured

def test_cli_browser(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sys, "argv", ["main.py", "browser"])
    monkeypatch.setattr("os.path.expanduser", lambda p: str(tmp_path) if "~" in p else p)
    from unittest.mock import patch
    with patch("cli.browser_repl.handle_browser") as mock_handle:
        from main import main
        main()
        assert mock_handle.called

def test_cli_browser_setup(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sys, "argv", ["main.py", "browser", "setup"])
    from main import main
    main()
    captured = capsys.readouterr().out
    assert "Browser Setup Diagnostics" in captured

def test_cli_skills(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sys, "argv", ["main.py", "skills"])
    from main import main
    main()
    captured = capsys.readouterr().out
    assert "Skills command executed." in captured

def test_cli_environment(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sys, "argv", ["main.py", "environment"])
    from main import main
    main()
    captured = capsys.readouterr().out
    assert "Environment command executed." in captured
