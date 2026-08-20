from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os
from pathlib import Path
from typing import Optional


def _parse_bool(value: Optional[str], default: bool) -> bool:
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


def _parse_int(value: Optional[str], default: int) -> int:
    """Parse an int from an environment variable string, returning *default* on failure."""
    if not value or not value.strip():
        return default
    try:
        return int(value.strip())
    except ValueError:
        return default


class Config(BaseModel):
    # Core
    openai_api_key: Optional[str] = Field(default=None)
    default_model: str = Field(default="gpt-4o")
    max_agent_steps: int = Field(default=40)

    # Paths / logging
    data_dir: str = Field(default="")
    log_level: str = Field(default="INFO")

    # Browser
    browser_host: str = Field(default="127.0.0.1")
    browser_ws_port: int = Field(default=18765)
    browser_http_port: int = Field(default=18766)
    browser_auto_start: bool = Field(default=False)

    # Memory
    memory_enabled: bool = Field(default=True)


def load_config() -> Config:
    load_dotenv()

    data_dir_raw = os.getenv("PYGENT_DATA_DIR")
    if not data_dir_raw:
        data_dir_raw = "~/.pygent"
    data_dir = str(Path(data_dir_raw).expanduser())

    return Config(
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        default_model=os.getenv("DEFAULT_MODEL", "gpt-4o"),
        max_agent_steps=_parse_int(os.getenv("MAX_AGENT_STEPS"), 40),

        data_dir=data_dir,
        log_level=os.getenv("PYGENT_LOG_LEVEL", "INFO"),

        browser_host=os.getenv("PYGENT_BROWSER_HOST", "127.0.0.1"),
        browser_ws_port=_parse_int(os.getenv("PYGENT_BROWSER_WS_PORT"), 18765),
        browser_http_port=_parse_int(os.getenv("PYGENT_BROWSER_HTTP_PORT"), 18766),
        browser_auto_start=_parse_bool(os.getenv("PYGENT_BROWSER_AUTO_START", ""), False),

        memory_enabled=_parse_bool(os.getenv("PYGENT_MEMORY_ENABLED", ""), True),
    )

def setup_data_directory(config: Config) -> None:
    if not config.data_dir:
        return
    base_dir = Path(config.data_dir)
    for subdir in ["memory", "skills", "sessions", "logs", "browser", "temp"]:
        (base_dir / subdir).mkdir(parents=True, exist_ok=True)
