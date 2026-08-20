import os
from config import Config, load_config, _parse_bool, _parse_int


# ---------------------------------------------------------------------------
# Helper unit tests
# ---------------------------------------------------------------------------

class TestParseBool:
    def test_true_values(self):
        for val in ("1", "true", "True", "TRUE", "yes", "YES", " true "):
            assert _parse_bool(val, False) is True

    def test_false_values(self):
        for val in ("0", "false", "False", "FALSE", "no", "NO", " false "):
            assert _parse_bool(val, True) is False

    def test_unrecognized_returns_default(self):
        assert _parse_bool("nope", True) is True
        assert _parse_bool("random", False) is False
        assert _parse_bool("maybe", True) is True

    def test_empty_returns_default(self):
        assert _parse_bool("", True) is True
        assert _parse_bool("", False) is False
        assert _parse_bool("  ", True) is True
        assert _parse_bool(None, True) is True


class TestParseInt:
    def test_valid(self):
        assert _parse_int("42", 0) == 42
        assert _parse_int(" 7 ", 0) == 7

    def test_invalid_returns_default(self):
        assert _parse_int("abc", 10) == 10

    def test_empty_returns_default(self):
        assert _parse_int("", 5) == 5
        assert _parse_int(None, 5) == 5
        assert _parse_int("  ", 5) == 5


# ---------------------------------------------------------------------------
# Config model defaults
# ---------------------------------------------------------------------------

class TestConfigDefaults:
    def test_defaults(self):
        cfg = Config()
        assert cfg.openai_api_key is None
        assert cfg.default_model == "gpt-4o"
        assert cfg.max_agent_steps == 40
        assert cfg.data_dir == ""
        assert cfg.log_level == "INFO"
        assert cfg.browser_host == "127.0.0.1"
        assert cfg.browser_ws_port == 18765
        assert cfg.browser_http_port == 18766
        assert cfg.browser_auto_start is False
        assert cfg.memory_enabled is True


# ---------------------------------------------------------------------------
# load_config integration tests
# ---------------------------------------------------------------------------

def _clear_env(monkeypatch):
    """Remove all Pygent-related env vars so tests start clean."""
    for key in (
        "OPENAI_API_KEY",
        "DEFAULT_MODEL",
        "MAX_AGENT_STEPS",
        "PYGENT_DATA_DIR",
        "PYGENT_LOG_LEVEL",
        "PYGENT_BROWSER_HOST",
        "PYGENT_BROWSER_WS_PORT",
        "PYGENT_BROWSER_HTTP_PORT",
        "PYGENT_BROWSER_AUTO_START",
        "PYGENT_MEMORY_ENABLED",
    ):
        monkeypatch.delenv(key, raising=False)


def test_load_config_defaults(monkeypatch):
    _clear_env(monkeypatch)
    cfg = load_config()
    assert cfg.openai_api_key is None
    assert cfg.default_model == "gpt-4o"
    assert cfg.max_agent_steps == 40
    assert cfg.data_dir == ""
    assert cfg.log_level == "INFO"
    assert cfg.browser_host == "127.0.0.1"
    assert cfg.browser_ws_port == 18765
    assert cfg.browser_http_port == 18766
    assert cfg.browser_auto_start is False
    assert cfg.memory_enabled is True


def test_load_config_all_env_vars(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    monkeypatch.setenv("DEFAULT_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("MAX_AGENT_STEPS", "20")
    monkeypatch.setenv("PYGENT_DATA_DIR", "/tmp/pygent")
    monkeypatch.setenv("PYGENT_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("PYGENT_BROWSER_HOST", "0.0.0.0")
    monkeypatch.setenv("PYGENT_BROWSER_WS_PORT", "19000")
    monkeypatch.setenv("PYGENT_BROWSER_HTTP_PORT", "19001")
    monkeypatch.setenv("PYGENT_BROWSER_AUTO_START", "true")
    monkeypatch.setenv("PYGENT_MEMORY_ENABLED", "false")

    cfg = load_config()
    assert cfg.openai_api_key == "sk-test-123"
    assert cfg.default_model == "gpt-4o-mini"
    assert cfg.max_agent_steps == 20
    assert cfg.data_dir == "/tmp/pygent"
    assert cfg.log_level == "DEBUG"
    assert cfg.browser_host == "0.0.0.0"
    assert cfg.browser_ws_port == 19000
    assert cfg.browser_http_port == 19001
    assert cfg.browser_auto_start is True
    assert cfg.memory_enabled is False


def test_load_config_invalid_int_falls_back(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("MAX_AGENT_STEPS", "not_a_number")
    cfg = load_config()
    assert cfg.max_agent_steps == 40


def test_load_config_empty_api_key_is_none(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "")
    cfg = load_config()
    assert cfg.openai_api_key is None


def test_load_config_data_dir_expanduser(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("PYGENT_DATA_DIR", "~/pygent_data")
    cfg = load_config()
    assert "~" not in cfg.data_dir
    assert cfg.data_dir.endswith("/pygent_data") or cfg.data_dir.endswith("\\pygent_data")


def test_removed_provider_fields():
    """Verify that the old provider-specific fields are gone."""
    cfg = Config()
    assert not hasattr(cfg, "anthropic_api_key")
    assert not hasattr(cfg, "gemini_api_key")
    assert not hasattr(cfg, "default_provider")
