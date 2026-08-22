# Unified Model Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a unified configuration system for OpenAI, NVIDIA NIM, and Google Gemini with API key fallbacks and custom base URLs.

**Architecture:** We will replace the current hardcoded OpenAI environment variable reading in `config.py` with a preset-based system, update `OpenAIProvider` to accept base URLs, and update the CLI's check command to provide clear diagnostics.

**Tech Stack:** Python 3.11+, Pydantic, pytest.

## Global Constraints

Target Python 3.11+
Keep dependencies minimal.
Backward compatibility must be preserved for existing configurations where possible.

---

### Task 1: Update Configuration Schema and Logic

**Files:**
- Modify: `config.py`
- Modify: `.env.example`
- Modify: `tests/test_config.py`

**Interfaces:**
- Produces: `Config` class with `provider`, `api_key`, `base_url`, `default_model` fields and an `openai_api_key` property. `load_config()` correctly uses `PROVIDER_PRESETS`.

- [ ] **Step 1: Write the failing tests**

```python
# In tests/test_config.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL due to missing fields/logic in Config.

- [ ] **Step 3: Write minimal implementation**

Update `config.py`:
1. Change `Config` fields: replace `openai_api_key` with `api_key: str | None = Field(default=None)`, add `base_url: str | None = Field(default=None)`. Add the `@property def openai_api_key(self): return self.api_key`.
2. In `load_config()`, define `PROVIDER_PRESETS` and resolve `api_key`, `base_url`, `default_model` based on `PYGENT_PROVIDER` and environment variables. (See spec for exact fallback rules).

Update `.env.example` to remove dead variables (browser config, memory enabled) and add the new unified configuration template.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add config.py .env.example tests/test_config.py
git commit -m "feat(config): implement unified provider presets and fallbacks"
```

---

### Task 2: Update Provider Integration

**Files:**
- Modify: `providers/factory.py`
- Modify: `providers/openai_provider.py`
- Modify: `tests/test_providers.py` (if necessary to accommodate init signature change)

**Interfaces:**
- Consumes: `Config` (with `api_key`, `base_url`, `provider`)
- Produces: `OpenAIProvider` configured with `api_key` and `base_url`.

- [ ] **Step 1: Write the failing tests**

```python
# In tests/test_providers.py
def test_openai_provider_init_with_base_url():
    from providers.openai_provider import OpenAIProvider
    provider = OpenAIProvider(api_key="test-key", base_url="http://localhost:1234/v1")
    assert provider.client.base_url == "http://localhost:1234/v1"

def test_factory_creates_correctly():
    from config import Config
    from providers.factory import create_provider
    cfg = Config(provider="nvidia", api_key="nv-key", base_url="https://integrate.api.nvidia.com/v1")
    provider = create_provider(cfg)
    assert provider.client.api_key == "nv-key"
    assert str(provider.client.base_url) == "https://integrate.api.nvidia.com/v1/"
```
*(Ensure any existing tests instantiating OpenAIProvider are updated if needed).*

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_providers.py -v`
Expected: FAIL due to missing `base_url` argument in `OpenAIProvider`.

- [ ] **Step 3: Write minimal implementation**

Update `providers/openai_provider.py`:
Change `__init__` to accept `base_url: str | None = None` and pass it to `OpenAI(api_key=api_key, base_url=base_url)`.

Update `providers/factory.py`:
```python
def create_provider(config: Config) -> BaseProvider:
    if not config.api_key:
        raise ValueError(
            f"API key must be set for provider '{config.provider}'. "
            f"Please set the appropriate environment variable (e.g. OPENAI_API_KEY, NVIDIA_API_KEY, or GEMINI_API_KEY)."
        )
    return OpenAIProvider(api_key=config.api_key, base_url=config.base_url)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_providers.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add providers/ tests/test_providers.py
git commit -m "feat(providers): pass base_url and api_key to underlying OpenAI client"
```

---

### Task 3: Update CLI Diagnostics

**Files:**
- Modify: `cli/commands.py`
- Modify: `tests/test_cli.py`

**Interfaces:**
- Consumes: `config` (to report `config.provider`, `config.default_model`, `config.base_url`, `config.api_key`).

- [ ] **Step 1: Write the failing tests**

```python
# In tests/test_cli.py (update test_cli_check_command_with_key)
def test_cli_check_command_with_key(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("PYGENT_PROVIDER", "google")
    monkeypatch.setenv("GEMINI_API_KEY", "gem-123")
    monkeypatch.setattr(sys, "argv", ["main.py", "check"])
    from main import main
    main()
    captured = capsys.readouterr()
    assert "Provider: google" in captured.out
    assert "Model: gemini-2.5-flash" in captured.out
    assert "API Key: Present" in captured.out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -k check -v`
Expected: FAIL (output format mismatch).

- [ ] **Step 3: Write minimal implementation**

Update `cli/commands.py`:
Modify `handle_check()` to print:
```python
def handle_check(db_path: str, skills_dir: str, config):
    print("Checking Configuration...")
    print(f"Provider: {config.provider}")
    print(f"Model: {config.default_model}")
    print(f"Base URL: {config.base_url or 'Default'}")
    if config.api_key:
        print("API Key: Present")
    else:
        print("API Key: MISSING")
    print("Checking Database...")
    store = MemoryStore(db_path, skills_dir=skills_dir)
    store.close()
    print(f"Database OK at {db_path}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add cli/commands.py tests/test_cli.py
git commit -m "feat(cli): enhance pygent check to report new provider config"
```

---
