from typing import Optional

from openai import OpenAI


class OpenAIWrapper:
    """A thin wrapper around the OpenAI client used by the LLM service."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: Optional[str] = None):
        self.api_key = api_key
        self.model = model
        if api_key:
            effective_base_url = base_url or "https://api.proxyapi.ru/openai/v1"
            self.client = OpenAI(api_key=api_key, base_url=effective_base_url)
        else:
            self.client = None

    def send_message(self, message: str, model: Optional[str] = None) -> str:
        if self.client is None:
            raise RuntimeError("OpenAI API key is not configured")
        response = self.client.chat.completions.create(
            model=model or self.model,
            messages=[{"role": "user", "content": message}],
        )
        return response.choices[0].message.content
