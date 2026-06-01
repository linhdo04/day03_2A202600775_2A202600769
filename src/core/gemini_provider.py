import time
from typing import Dict, Any, Optional, Generator
from google import genai
from google.genai import errors as genai_errors
from src.core.llm_provider import LLMProvider

_MAX_RETRIES = 4
_RETRY_DELAY = 12  # seconds — gemini-2.5-flash needs longer back-off on 503


class GeminiProvider(LLMProvider):
    def __init__(self, model_name: str = "gemini-1.5-flash", api_key: Optional[str] = None):
        super().__init__(model_name, api_key)
        self.client = genai.Client(api_key=self.api_key)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()

        contents = prompt
        config = {}
        if system_prompt:
            config["system_instruction"] = system_prompt

        last_error = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config if config else None,
                )
                break
            except genai_errors.ServerError as e:
                last_error = e
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_RETRY_DELAY * (attempt + 1))
                else:
                    raise
        else:
            raise last_error

        latency_ms = int((time.time() - start_time) * 1000)
        usage_meta = response.usage_metadata
        usage = {
            "prompt_tokens": usage_meta.prompt_token_count or 0,
            "completion_tokens": usage_meta.candidates_token_count or 0,
            "total_tokens": usage_meta.total_token_count or 0,
        }

        return {
            "content": response.text,
            "usage": usage,
            "latency_ms": latency_ms,
            "provider": "google",
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        config = {}
        if system_prompt:
            config["system_instruction"] = system_prompt

        for chunk in self.client.models.generate_content_stream(
            model=self.model_name,
            contents=prompt,
            config=config if config else None,
        ):
            if chunk.text:
                yield chunk.text
