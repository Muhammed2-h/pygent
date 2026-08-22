import os

from config import Config, _parse_int, load_config

# ---------------------------------------------------------------------------
# Helper unit tests
# ---------------------------------------------------------------------------

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
        "PYGENT_PROVIDER",
        "NVIDIA_API_KEY",
        "GEMINI_API_KEY",
        "PYGENT_API_KEY",
        "OPENAI_BASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)


def test_load_config_defaults(monkeypatch):
    _clear_env(monkeypatch)
    cfg = load_config()
    assert cfg.openai_api_key is None
    assert cfg.default_model == "gpt-4o"
    assert cfg.max_agent_steps == 40
    assert cfg.data_dir == str(os.path.expanduser("~/.pygent"))
    assert cfg.log_level == "INFO"


def test_load_config_all_env_vars(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    monkeypatch.setenv("DEFAULT_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("MAX_AGENT_STEPS", "20")
    monkeypatch.setenv("PYGENT_DATA_DIR", "/tmp/pygent")
    monkeypatch.setenv("PYGENT_LOG_LEVEL", "DEBUG")

    cfg = load_config()
    assert cfg.openai_api_key == "sk-test-123"
    assert cfg.default_model == "gpt-4o-mini"
    assert cfg.max_agent_steps == 20
    assert cfg.data_dir == "/tmp/pygent"
    assert cfg.log_level == "DEBUG"


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


def test_load_config_nvidia_preset(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("PYGENT_PROVIDER", "nvidia")
    monkeypatch.setenv("NVIDIA_API_KEY", "nv-123")
    cfg = load_config()
    assert cfg.provider == "nvidia"
    assert cfg.api_key == "nv-123"
    assert cfg.base_url == "https://integrate.api.nvidia.com/v1"
    assert cfg.default_model == "meta/llama-3.3-70b-instruct"
    assert cfg.openai_api_key == "nv-123"

def test_load_config_gemini_preset(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("PYGENT_PROVIDER", "google")
    monkeypatch.setenv("GEMINI_API_KEY", "gem-123")
    cfg = load_config()
    assert cfg.provider == "google"
    assert cfg.api_key == "gem-123"
    assert cfg.base_url == "https://generativelanguage.googleapis.com/v1beta/openai/"
    assert cfg.default_model == "gemini-2.5-flash"

def test_load_config_custom_preset_and_overrides(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("PYGENT_PROVIDER", "custom")
    monkeypatch.setenv("PYGENT_API_KEY", "custom-123")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("DEFAULT_MODEL", "llama3")
    cfg = load_config()
    assert cfg.provider == "custom"
    assert cfg.api_key == "custom-123"
    assert cfg.base_url == "http://localhost:11434/v1"
    assert cfg.default_model == "llama3"
