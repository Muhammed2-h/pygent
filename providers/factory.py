from config import Config

from .base import BaseProvider
from .openai_provider import OpenAIProvider


def create_provider(config: Config) -> BaseProvider:
    provider_type = getattr(config, "provider", "openai")
    
    if provider_type == "openai":
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY must be set when using openai provider")
        return OpenAIProvider(config.openai_api_key)
    else:
        raise ValueError(f"Unsupported provider: {provider_type}")
