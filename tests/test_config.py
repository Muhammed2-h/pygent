import os
from config import Config, load_config

def test_load_config(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test_key")
    monkeypatch.setenv("MAX_AGENT_STEPS", "5")
    config = load_config()
    assert config.openai_api_key == "test_key"
    assert config.max_agent_steps == 5
    assert config.default_provider == "openai"

def test_load_config_defaults(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("DEFAULT_PROVIDER", raising=False)
    monkeypatch.delenv("DEFAULT_MODEL", raising=False)
    monkeypatch.delenv("MAX_AGENT_STEPS", raising=False)
    
    config = load_config()
    assert config.openai_api_key is None
    assert config.anthropic_api_key is None
    assert config.gemini_api_key is None
    assert config.default_provider == "openai"
    assert config.default_model == "gpt-4o"
    assert config.max_agent_steps == 8

def test_load_config_all_env_vars(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-123")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-123")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-123")
    monkeypatch.setenv("DEFAULT_PROVIDER", "anthropic")
    monkeypatch.setenv("DEFAULT_MODEL", "claude-3-5-sonnet")
    monkeypatch.setenv("MAX_AGENT_STEPS", "12")
    
    config = load_config()
    assert config.openai_api_key == "sk-openai-123"
    assert config.anthropic_api_key == "sk-ant-123"
    assert config.gemini_api_key == "gemini-123"
    assert config.default_provider == "anthropic"
    assert config.default_model == "claude-3-5-sonnet"
    assert config.max_agent_steps == 12
