import json
import logging
from abc import ABC, abstractmethod

import tiktoken

from app.core.config import settings
from app.providers.base_llm import BaseLLMProvider

logger = logging.getLogger(__name__)

MAP_SYSTEM_PROMPT = (
    "Ты — эксперт по анализу видео-контента. "
    "Извлеки из данного фрагмента транскрипта:\n"
    "1. Ключевые идеи и тезисы\n"
    "2. Конкретные факты, цифры, примеры\n"
    "3. Цитаты спикера\n"
    "4. Структуру аргументации\n\n"
    "Сохраняй техническую точность. Не добавляй ничего от себя. "
    "Отвечай на русском языке."
)

MEDIUM_SYSTEM_PROMPT = (
    "Ты — профессиональный автор статей. "
    "На основе предоставленных саммари фрагментов видео напиши развёрнутую "
    "статью для платформы Medium.\n\n"
    "Требования:\n"
    "- Формат: Markdown\n"
    "- Объём: 1500–3000 слов\n"
    "- Тон: разговорно-экспертный\n"
    "- Структура: заголовок, вступление с hook, подзаголовки, заключение\n"
    "- Язык: СТРОГО русский, независимо от языка исходного контента"
)

HABR_SYSTEM_PROMPT = (
    "Ты — профессиональный технический автор. "
    "На основе предоставленных саммари фрагментов видео напиши техническую "
    "статью для Habr.\n\n"
    "Требования:\n"
    "- Формат: Markdown\n"
    "- Объём: 1500–3000 слов\n"
    "- Тон: формально-технический\n"
    "- Структура: заголовок, оглавление, подробные разделы, примеры, заключение\n"
    "- Язык: СТРОГО русский, независимо от языка исходного контента"
)

LINKEDIN_SYSTEM_PROMPT = (
    "Ты — эксперт по LinkedIn-контенту. "
    "На основе предоставленных саммари фрагментов видео напиши пост "
    "для LinkedIn.\n\n"
    "Требования:\n"
    "- Объём: 500–1300 символов\n"
    "- Тон: профессиональный\n"
    "- Структура: hook-фраза в первой строке, ключевой инсайт, CTA в конце\n"
    "- Язык: СТРОГО русский, независимо от языка исходного контента"
)

REVISION_ADDENDUM = (
    "\n\nВНИМАНИЕ: предыдущая версия текста была отклонена редактором. "
    "Ниже отчёт о проблемах:\n{report}\n\n"
    "Исправь указанные проблемы, сохраняя корректные части текста. "
    "Предыдущая версия текста для контекста:\n{previous_text}"
)


class BaseGeneratorService(ABC):
    @abstractmethod
    def chunk_transcript(self, text: str) -> list[str]: ...

    @abstractmethod
    def map_chunks(self, chunks: list[str]) -> list[str]: ...

    @abstractmethod
    def reduce(
        self,
        summaries: list[str],
        validation_report: dict | None = None,
        previous_texts: dict | None = None,
    ) -> dict: ...


class GeneratorService(BaseGeneratorService):
    def __init__(self, llm: BaseLLMProvider) -> None:
        self.llm = llm
        self._enc = tiktoken.get_encoding("cl100k_base")

    def chunk_transcript(
        self, text: str, chunk_size: int = 3000, overlap: int = 200
    ) -> list[str]:
        tokens = self._enc.encode(text)
        chunks: list[str] = []
        start = 0
        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            chunks.append(self._enc.decode(tokens[start:end]))
            if end >= len(tokens):
                break
            start = end - overlap
        return chunks if chunks else [text]

    def map_chunks(self, chunks: list[str]) -> list[str]:
        summaries: list[str] = []
        for i, chunk in enumerate(chunks):
            logger.info("Mapping chunk %d/%d", i + 1, len(chunks))
            summary = self.llm.complete(MAP_SYSTEM_PROMPT, chunk, settings.map_model)
            summaries.append(summary)
        return summaries

    def reduce(
        self,
        summaries: list[str],
        validation_report: dict | None = None,
        previous_texts: dict | None = None,
    ) -> dict:
        combined = "\n\n---\n\n".join(summaries)

        def _prompt(base: str, platform: str) -> str:
            prompt = base
            if validation_report and previous_texts:
                platform_report = validation_report.get(platform, {})
                prev = previous_texts.get(f"{platform}_text", "")
                prompt += REVISION_ADDENDUM.format(
                    report=json.dumps(platform_report, ensure_ascii=False),
                    previous_text=prev,
                )
            return prompt

        medium = self.llm.complete(
            _prompt(MEDIUM_SYSTEM_PROMPT, "medium"), combined, settings.reduce_model
        )
        habr = self.llm.complete(
            _prompt(HABR_SYSTEM_PROMPT, "habr"), combined, settings.reduce_model
        )
        linkedin = self.llm.complete(
            _prompt(LINKEDIN_SYSTEM_PROMPT, "linkedin"), combined, settings.reduce_model
        )

        return {
            "medium_text": medium,
            "habr_text": habr,
            "linkedin_text": linkedin,
            "reduce_summary_text": combined,
        }
