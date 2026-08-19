from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os
from typing import Optional

class Config(BaseModel):
    openai_api_key: Optional[str] = Field(default=None)
    anthropic_api_key: Optional[str] = Field(default=None)
    gemini_api_key: Optional[str] = Field(default=None)
    default_provider: str = Field(default="openai")
    default_model: str = Field(default="gpt-4o")
    max_agent_steps: int = Field(default=8)

def load_config() -> Config:
    load_dotenv()
    max_steps_env = os.getenv("MAX_AGENT_STEPS")
    max_steps = int(max_steps_env) if max_steps_env and max_steps_env.strip() else 8
    return Config(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        default_provider=os.getenv("DEFAULT_PROVIDER", "openai"),
        default_model=os.getenv("DEFAULT_MODEL", "gpt-4o"),
        max_agent_steps=max_steps
    )
