import json
import logging
import re

from openai import OpenAI

from app.core.config import settings
from app.providers.base_llm import BaseLLMProvider

logger = logging.getLogger(__name__)


class LocalLLMProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self.client = OpenAI(
            base_url=settings.local_llm_base_url,
            api_key="ollama",
        )

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
        try:
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
        except Exception as exc:
            if "response_format" not in str(exc).lower():
                raise
            logger.warning(
                "Model %s does not support response_format; "
                "falling back to raw completion with JSON extraction",
                model,
            )

        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )
        text = response.choices[0].message.content or ""
        return self._extract_json(text)

    @staticmethod
    def _extract_json(text: str) -> dict:
        fenced = re.search(r"```(?:json)?\s*(\{.*?})\s*```", text, re.DOTALL)
        if fenced:
            return json.loads(fenced.group(1))

        match = re.search(r"\{.*}", text, re.DOTALL)
        if match:
            return json.loads(match.group())

        raise ValueError(f"Could not extract JSON from LLM response: {text[:200]}")
