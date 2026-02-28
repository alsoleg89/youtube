import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import tiktoken

from app.core.config import settings
from app.providers.base_llm import BaseLLMProvider

logger = logging.getLogger(__name__)

MAP_SYSTEM_PROMPT = (
    "Ты — эксперт по анализу контента. "
    "Извлеки из данного фрагмента текста:\n"
    "1. Ключевые идеи и тезисы\n"
    "2. Конкретные факты, цифры, примеры\n"
    "3. Цитаты автора/спикера\n"
    "4. Структуру аргументации\n\n"
    "Сохраняй техническую точность. Не добавляй ничего от себя. "
    "Отвечай на русском языке."
)

_ANTI_HALLUCINATION = (
    "\n\nСТРОГО ЗАПРЕЩЕНО:\n"
    "- Придумывать факты, цифры, статистику, даты или имена, которых нет в саммари\n"
    "- Ссылаться на исследования или источники, не упомянутые в саммари\n"
    "- Додумывать детали сюжета, кастинга или характеристики, если они не упоминаются\n"
    "- Добавлять «воду» для увеличения объема текста\n"
    "Используй ТОЛЬКО информацию из предоставленных саммари. "
    "Если данных недостаточно — обобщай, но не выдумывай конкретику."
)

MEDIUM_SYSTEM_PROMPT = (
    "Ты — профессиональный автор статей. "
    "На основе предоставленных саммари фрагментов напиши развёрнутую "
    "статью для платформы Medium.\n\n"
    "Требования:\n"
    "- Формат: Markdown\n"
    "- Объём: адаптируй под количество материала (от 500 до 2000 слов), не "
    "добавляй воду ради объема\n"
    "- Тон: разговорно-экспертный\n"
    "- Структура: заголовок, вступление с hook, подзаголовки, заключение\n"
    "- Язык: СТРОГО русский, независимо от языка исходного контента"
    + _ANTI_HALLUCINATION
)

HABR_SYSTEM_PROMPT = (
    "Ты — профессиональный технический автор. "
    "На основе предоставленных саммари фрагментов напиши техническую "
    "статью для Habr.\n\n"
    "Требования:\n"
    "- Формат: Markdown\n"
    "- Объём: адаптируй под количество материала (от 500 до 2000 слов), не "
    "добавляй воду ради объема\n"
    "- Тон: формально-технический\n"
    "- Структура: заголовок, оглавление, подробные разделы, примеры, заключение\n"
    "- Язык: СТРОГО русский, независимо от языка исходного контента"
    + _ANTI_HALLUCINATION
)

LINKEDIN_SYSTEM_PROMPT = (
    "Ты — эксперт по LinkedIn-контенту. "
    "На основе предоставленных саммари фрагментов напиши пост "
    "для LinkedIn.\n\n"
    "Требования:\n"
    "- Объём: 500–1300 символов\n"
    "- Тон: профессиональный\n"
    "- Структура: hook-фраза в первой строке, ключевой инсайт, CTA в конце\n"
    "- Язык: СТРОГО русский, независимо от языка исходного контента"
    + _ANTI_HALLUCINATION
)

RESEARCH_SYSTEM_PROMPT = (
    "Ты — профессиональный академический автор. "
    "На основе предоставленных саммари фрагментов напиши академическую "
    "статью в стиле ResearchGate.\n\n"
    "Требования:\n"
    "- Формат: Markdown\n"
    "- Объём: адаптируй под количество материала (от 1000 до 3000 слов), не "
    "добавляй воду ради объема\n"
    "- Тон: формальный, академический\n"
    "- Структура: Abstract, Introduction, Main Body с подразделами, "
    "Discussion, Conclusion, References (если есть)\n"
    "- Используй пассивный залог и научную лексику\n"
    "- Язык: СТРОГО русский, независимо от языка исходного контента"
    + _ANTI_HALLUCINATION
)

BANANA_SYSTEM_PROMPT = (
    "Ты — режиссёр-визуализатор. На основе предоставленных саммари фрагментов "
    "создай видео-промпт для генерации AI-видео.\n\n"
    "Ответ СТРОГО в формате JSON:\n"
    "{\n"
    '  "style_summary": "описание визуального стиля видео (кинематографичный, '
    'минималистичный, и т.д.)",\n'
    '  "scenes": [\n'
    "    {\n"
    '      "scene_number": 1,\n'
    '      "visual_prompt": "детальное описание кадра для генератора изображений",\n'
    '      "voiceover_text": "текст голосового сопровождения для этой сцены"\n'
    "    }\n"
    "  ]\n"
    "}\n\n"
    "Требования:\n"
    "- 5–12 сцен\n"
    "- visual_prompt: детальный, описательный (на английском языке для совместимости с генераторами)\n"
    "- voiceover_text: на русском языке\n"
    "- Каждая сцена должна логически следовать из предыдущей"
)

REVISION_ADDENDUM = (
    "\n\nВНИМАНИЕ: предыдущая версия текста была отклонена редактором. "
    "Ниже отчёт о проблемах:\n{report}\n\n"
    "Исправь указанные проблемы, сохраняя корректные части текста. "
    "Если проблема — галлюцинация: УДАЛИ все факты, цифры и утверждения, "
    "которых нет в исходных саммари. Не заменяй их другими выдуманными — просто убери.\n"
    "Предыдущая версия текста для контекста:\n{previous_text}"
)

CHANNEL_DEFS: list[tuple[str, str, str, bool]] = [
    ("medium_text", "medium", MEDIUM_SYSTEM_PROMPT, False),
    ("habr_text", "habr", HABR_SYSTEM_PROMPT, False),
    ("linkedin_text", "linkedin", LINKEDIN_SYSTEM_PROMPT, False),
    ("research_article", "research_article", RESEARCH_SYSTEM_PROMPT, False),
    ("banana_video_prompt", "banana_video_prompt", BANANA_SYSTEM_PROMPT, True),
]

ALL_CHANNEL_KEYS = [key for key, *_ in CHANNEL_DEFS]

PAYLOAD_KEY_TO_PLATFORM: dict[str, str] = {key: platform for key, platform, _, _ in CHANNEL_DEFS}
PLATFORM_TO_PAYLOAD_KEY: dict[str, str] = {platform: key for key, platform, _, _ in CHANNEL_DEFS}


class GeneratorService:
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

    def map_chunks(self, chunks: list[str], max_workers: int = 8) -> list[str]:
        total = len(chunks)
        results: list[tuple[int, str]] = []

        def _map_one(idx: int, chunk: str) -> tuple[int, str]:
            logger.info("Mapping chunk %d/%d", idx + 1, total)
            return idx, self.llm.complete(MAP_SYSTEM_PROMPT, chunk, settings.map_model)

        with ThreadPoolExecutor(max_workers=min(max_workers, total)) as pool:
            futures = {pool.submit(_map_one, i, c): i for i, c in enumerate(chunks)}
            for future in as_completed(futures):
                results.append(future.result())

        results.sort(key=lambda x: x[0])
        return [text for _, text in results]

    def reduce(
        self,
        summaries: list[str],
        validation_report: dict | None = None,
        previous_texts: dict | None = None,
        channels: list[str] | None = None,
    ) -> dict:
        combined = "\n\n---\n\n".join(summaries)
        target_keys = set(channels) if channels else {k for k, *_ in CHANNEL_DEFS}

        tasks: list[tuple[str, str, str, bool]] = []
        for key, platform, prompt_template, is_json in CHANNEL_DEFS:
            if key not in target_keys:
                continue
            system_prompt = prompt_template
            if validation_report and previous_texts:
                platform_report = validation_report.get(platform, {})
                prev = previous_texts.get(key, "") or previous_texts.get(platform, "")
                system_prompt += REVISION_ADDENDUM.format(
                    report=json.dumps(platform_report, ensure_ascii=False),
                    previous_text=prev,
                )
            tasks.append((key, system_prompt, combined, is_json))

        result: dict = {}

        def _gen(item: tuple[str, str, str, bool]) -> tuple[str, str | dict]:
            key, sys_prompt, user_text, is_json = item
            if is_json:
                return key, self.llm.complete_json(sys_prompt, user_text, settings.reduce_model)
            return key, self.llm.complete(sys_prompt, user_text, settings.reduce_model)

        with ThreadPoolExecutor(max_workers=min(5, len(tasks))) as pool:
            futures = {pool.submit(_gen, t): t[0] for t in tasks}
            for future in as_completed(futures):
                key, value = future.result()
                result[key] = value

        result["reduce_summary_text"] = combined
        return result
