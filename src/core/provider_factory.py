import os
from dotenv import load_dotenv
from src.core.llm_provider import LLMProvider


def create_provider() -> LLMProvider:
    """
    Returns a GeminiProvider using GEMINI_API_KEY from .env.
    Model is set via DEFAULT_MODEL (default: gemini-1.5-flash).
    """
    load_dotenv()
    from src.core.gemini_provider import GeminiProvider

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in your .env file.")

    model = os.getenv("DEFAULT_MODEL", "gemini-1.5-flash")
    return GeminiProvider(model_name=model, api_key=api_key)
