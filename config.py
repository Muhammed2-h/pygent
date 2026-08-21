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
    openai_api_key: str | None = Field(default=None)
    default_model: str = Field(default="gpt-4o")
    max_agent_steps: int = Field(default=40)

    # Paths / logging
    data_dir: str = Field(default="")
    log_level: str = Field(default="INFO")




def load_config() -> Config:
    load_dotenv()

    data_dir_raw = os.getenv("PYGENT_DATA_DIR")
    if not data_dir_raw:
        data_dir_raw = "~/.pygent"
    data_dir = str(Path(data_dir_raw).expanduser())

    return Config(
        provider=os.getenv("PYGENT_PROVIDER", "openai"),
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        default_model=os.getenv("DEFAULT_MODEL", "gpt-4o"),
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
