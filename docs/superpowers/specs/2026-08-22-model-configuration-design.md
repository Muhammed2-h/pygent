# Specification: Unified Model Integration & API Key Configuration

## 1. Overview & Motivation
Pygent requires a consistent, scalable, and easy-to-maintain configuration structure for LLMs that:
- Eliminates unused / dead configuration variables in `.env.example` and `config.py`.
- Natively supports **OpenAI**, **NVIDIA NIM**, and **Google Gemini** (via OpenAI-compatible endpoints) without adding heavy vendor SDK dependencies.
- Supports arbitrary custom OpenAI-compatible endpoints (Ollama, vLLM, OpenRouter, DeepSeek, LocalAI) via `OPENAI_BASE_URL` / `PYGENT_BASE_URL`.
- Provides sensible default models and endpoint URLs for each provider preset while allowing zero-friction overrides.
- Preserves full backward compatibility with existing tests and codebase callers.

---

## 2. Architecture & Preset Mapping

### 2.1 Provider Presets

| Provider Preset (`PYGENT_PROVIDER`) | Default Base URL | API Key Candidates (Order of Resolution) | Default Model |
| :--- | :--- | :--- | :--- |
| `openai` *(default)* | `None` *(uses OpenAI official endpoint)* | `OPENAI_API_KEY`, `PYGENT_API_KEY` | `gpt-4o` |
| `nvidia` | `https://integrate.api.nvidia.com/v1` | `NVIDIA_API_KEY`, `OPENAI_API_KEY`, `PYGENT_API_KEY` | `meta/llama-3.3-70b-instruct` |
| `google` / `gemini` | `https://generativelanguage.googleapis.com/v1beta/openai/` | `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `OPENAI_API_KEY` | `gemini-2.5-flash` |
| `custom` | `None` *(requires `OPENAI_BASE_URL` or `PYGENT_BASE_URL`)* | `OPENAI_API_KEY`, `PYGENT_API_KEY` | `gpt-4o` |

---

## 3. Configuration & Environment (`config.py`)

### 3.1 `Config` Model
```python
class Config(BaseModel):
    # Provider & Model Settings
    provider: str = Field(default="openai")
    api_key: str | None = Field(default=None)
    base_url: str | None = Field(default=None)
    default_model: str = Field(default="gpt-4o")
    max_agent_steps: int = Field(default=40)

    # Runtime Paths & Logging
    data_dir: str = Field(default="")
    log_level: str = Field(default="INFO")

    @property
    def openai_api_key(self) -> str | None:
        """Backward compatibility alias for api_key."""
        return self.api_key
```

### 3.2 Resolution Logic in `load_config()`
1. Read `PYGENT_PROVIDER` (default `"openai"`). Normalize to lowercase.
2. Lookup preset metadata from `PROVIDER_PRESETS`.
3. Resolve `api_key`: Check candidate env vars in priority order for the preset.
4. Resolve `base_url`: Check `OPENAI_BASE_URL` or `PYGENT_BASE_URL`, falling back to preset `default_base_url`.
5. Resolve `default_model`: Check `DEFAULT_MODEL` or `OPENAI_MODEL` or `PYGENT_MODEL`, falling back to preset `default_model`.
6. Resolve `data_dir` and `log_level` with standard defaults.

---

## 4. Provider Implementation (`providers/`)

### 4.1 Factory (`providers/factory.py`)
- Reads `config.provider`, `config.api_key`, and `config.base_url`.
- Validates that `config.api_key` is provided. If missing, raises a clear `ValueError` detailing the expected environment variable(s) for that provider.
- Returns `OpenAIProvider(api_key=config.api_key, base_url=config.base_url)`.

### 4.2 `OpenAIProvider` (`providers/openai_provider.py`)
- Updated `__init__(self, api_key: str, base_url: str | None = None)` to pass `base_url` to `OpenAI(api_key=api_key, base_url=base_url)`.
- Existing retry logic, exponential backoff, context truncation, and function call parsing remain completely unified and shared across all providers.

---

## 5. CLI Diagnostics (`cli/commands.py`)
- Update `handle_check` to report the active provider, model, base URL (if non-default), and key status clearly during `pygent check`.

---

## 6. `.env.example` & Documentation
- Clean `.env.example` to remove obsolete browser port / memory flags from previous iterations.
- Document clear configuration examples for OpenAI, NVIDIA NIM, Google Gemini, and custom local endpoints (Ollama, vLLM, OpenRouter).

---

## 7. Testing & Verification Plan
- **Unit Tests for Config:** Test all presets (`openai`, `nvidia`, `google`, `custom`), fallback key resolution, base URL overrides, and default model assignments.
- **Provider Tests:** Test that `OpenAIProvider` accepts `base_url` and correctly configures the underlying client.
- **CLI Tests:** Verify `pygent check` outputs the provider and key status cleanly.
- **Full Test Suite:** Ensure all 388 existing tests pass with 100% backward compatibility.
