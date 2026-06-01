import os
from dotenv import load_dotenv
from src.core.llm_provider import LLMProvider


def create_provider() -> LLMProvider:
    load_dotenv()
    provider_name = os.getenv("DEFAULT_PROVIDER", "google").lower()
    model = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")

    if provider_name == "google":
        from src.core.gemini_provider import GeminiProvider
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in your .env file.")
        return GeminiProvider(model_name=model, api_key=api_key)

    elif provider_name == "openai":
        from src.core.openai_provider import OpenAIProvider
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set in your .env file.")
        return OpenAIProvider(model_name=model, api_key=api_key)

    elif provider_name == "local":
        from src.core.local_provider import LocalProvider
        model_path = os.getenv("LOCAL_MODEL_PATH", "./models/P")
        return LocalProvider(model_path=model_path)

    else:
        raise ValueError(
            f"Unknown provider '{provider_name}'. "
            "Set DEFAULT_PROVIDER to 'google', 'openai', or 'local' in your .env file."
        )
        
