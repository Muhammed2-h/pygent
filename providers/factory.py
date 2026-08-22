from config import Config

from .base import BaseProvider
from .openai_provider import OpenAIProvider


def create_provider(config: Config) -> BaseProvider:
    if not config.api_key:
        raise ValueError(
            f"API key must be set for provider '{config.provider}'. "
            f"Please set the appropriate environment variable (e.g. OPENAI_API_KEY, NVIDIA_API_KEY, or GEMINI_API_KEY)."
        )
    return OpenAIProvider(api_key=config.api_key, base_url=config.base_url)
