import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


def _parse_bool(value: str | None, default: bool) -> bool:
    """Parse a boolean from an environment variable string.

    Returns *default* when *value* is empty/None or not a recognised
    boolean string (mirrors ``_parse_int`` fallback behaviour).
    """
    if not value or not value.strip():
        return default
    normalised = value.strip().lower()
    if normalised in ("1", "true", "yes"):
        return True
    if normalised in ("0", "false", "no"):
        return False
    return default


def _parse_int(value: str | None, default: int) -> int:
    """Parse an int from an environment variable string, returning *default* on failure."""
    if not value or not value.strip():
        return default
    try:
        return int(value.strip())
    except ValueError:
        return default


class Config(BaseModel):
    # Core
    provider: str = Field(default="openai")
    api_key: str | None = Field(default=None)
    base_url: str | None = Field(default=None)
    default_model: str = Field(default="gpt-4o")
    max_agent_steps: int = Field(default=40)

    # Paths / logging
    data_dir: str = Field(default="")
    log_level: str = Field(default="INFO")

    @property
    def openai_api_key(self) -> str | None:
        return self.api_key




def load_config() -> Config:
    load_dotenv()

    data_dir_raw = os.getenv("PYGENT_DATA_DIR")
    if not data_dir_raw:
        data_dir_raw = "~/.pygent"
    data_dir = str(Path(data_dir_raw).expanduser())

    provider = os.getenv("PYGENT_PROVIDER", "openai")

    PROVIDER_PRESETS = {
        "openai": {
            "env_key": "OPENAI_API_KEY",
            "base_url": None,
            "default_model": "gpt-4o",
        },
        "nvidia": {
            "env_key": "NVIDIA_API_KEY",
            "base_url": "https://integrate.api.nvidia.com/v1",
            "default_model": "meta/llama-3.3-70b-instruct",
        },
        "google": {
            "env_key": "GEMINI_API_KEY",
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "default_model": "gemini-2.5-flash",
        },
    }

    preset = PROVIDER_PRESETS.get(provider, {})
    env_key = preset.get("env_key", f"{provider.upper()}_API_KEY")
    
    api_key = os.getenv(env_key)
    if not api_key:
        api_key = os.getenv("PYGENT_API_KEY")

    base_url = os.getenv("OPENAI_BASE_URL") or preset.get("base_url")
    default_model = os.getenv("DEFAULT_MODEL") or preset.get("default_model", "gpt-4o")

    return Config(
        provider=provider,
        api_key=api_key or None,
        base_url=base_url or None,
        default_model=default_model,
        max_agent_steps=_parse_int(os.getenv("MAX_AGENT_STEPS"), 40),
        data_dir=data_dir,
        log_level=os.getenv("PYGENT_LOG_LEVEL", "INFO"),
    )

def setup_data_directory(config: Config) -> None:
    if not config.data_dir:
        return
    base_dir = Path(config.data_dir)
    for subdir in ["memory", "skills", "sessions", "logs", "browser", "temp"]:
        (base_dir / subdir).mkdir(parents=True, exist_ok=True)
