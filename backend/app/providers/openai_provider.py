import json
import logging

from openai import OpenAI

from app.core.config import settings
from app.providers.base_llm import BaseLLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.openai_api_key)

    def complete(self, system_prompt: str, user_prompt: str, model: str) -> str:
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content or ""

    def complete_json(self, system_prompt: str, user_prompt: str, model: str) -> dict:
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content or "{}"
        return json.loads(text)
