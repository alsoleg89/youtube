import logging

import tiktoken

from app.core.config import settings
from app.providers.base_llm import BaseLLMProvider
from app.services.generator import PAYLOAD_KEY_TO_PLATFORM, PLATFORM_TO_PAYLOAD_KEY

logger = logging.getLogger(__name__)

MAX_TRANSCRIPT_TOKENS_FOR_VALIDATION = 60_000

VALIDATOR_SYSTEM_PROMPT = (
    "Ты — строгий, но справедливый редактор-фактчекер. Проверь предоставленные тексты, написанные для "
    "разных платформ, по трём критериям.\n\n"
    "Для каждого критерия определи, пройдена ли проверка (passed: true/false), "
    "и дай краткое пояснение (details).\n\n"
    "Критерии:\n"
    "1. policy_risk — содержит ли текст потенциально опасный, незаконный, "
    "оскорбительный или неэтичный контент?\n"
    "2. hallucination — содержит ли текст ВЫДУМАННЫЕ факты: конкретные цифры, "
    "статистику, даты, имена людей или названия организаций, "
    "которых НЕТ в оригинальном тексте (транскрипте/саммари)?\n"
    "   САМОЕ ВАЖНОЕ: \n"
    "   - Оценочные суждения (например, 'оказал огромное влияние', 'стал хитом'), "
    "логические выводы, обобщения, метафоры, анализ динамики событий/персонажей — это НЕ галлюцинации!\n"
    "   - Мелкие неточности, синонимы или округления (например, '15-16' вместо '15') — это НЕ галлюцинации!\n"
    "   - Отсутствие каких-либо фактов из оригинала в сгенерированном тексте — это НЕ галлюцинация! Текст не обязан перечислять всё.\n"
    "   - Перефразирование и добавление общеизвестного контекста для связности — это НЕ галлюцинация.\n"
    "   - Галлюцинация — это ТОЛЬКО откровенно выдуманные КОНКРЕТНЫЕ факты (неправильные даты, несуществующие имена, ложная статистика), которых нет в исходнике и которые радикально искажают смысл.\n"
    "   Если сомневаешься, или если это просто аналитический вывод из текста, считай, что проверка пройдена (passed: true).\n"
    "3. tone_mismatch — соответствует ли тон и стиль текста целевой платформе?\n\n"
    'Ответ строго в формате JSON, где ключи - это названия платформ, '
    'а значения - результаты проверок:\n'
    '{\n'
    '  "PLATFORM_NAME": {\n'
    '    "checks": [\n'
    '      {"name": "policy_risk", "passed": true, "details": "..."},\n'
    '      {"name": "hallucination", "passed": true, "details": "..."},\n'
    '      {"name": "tone_mismatch", "passed": true, "details": "..."}\n'
    '    ]\n'
    '  }\n'
    '}'
)

SCENE_REQUIRED_KEYS = {"scene_number", "visual_prompt", "voiceover_text"}


class ValidatorService:
    def __init__(self, llm: BaseLLMProvider) -> None:
        self.llm = llm
        self._enc = tiktoken.get_encoding("cl100k_base")

    def _truncate_transcript(self, transcript: str) -> str:
        tokens = self._enc.encode(transcript)
        if len(tokens) <= MAX_TRANSCRIPT_TOKENS_FOR_VALIDATION:
            return transcript
        logger.warning(
            "Truncating transcript from %d to %d tokens for validation",
            len(tokens),
            MAX_TRANSCRIPT_TOKENS_FOR_VALIDATION,
        )
        return self._enc.decode(tokens[:MAX_TRANSCRIPT_TOKENS_FOR_VALIDATION])

    def validate(
        self,
        texts: dict,
        transcript: str,
        channels: list[str] | None = None,
    ) -> dict:
        report: dict = {}
        all_passed = True

        truncated = self._truncate_transcript(transcript)

        target_keys = set(channels) if channels else None

        text_channels = {
            "medium": "medium_text",
            "habr": "habr_text",
            "linkedin": "linkedin_text",
            "research_article": "research_article",
        }

        platforms_to_check = {}
        for platform, key in text_channels.items():
            if target_keys is not None and key not in target_keys:
                continue
            text = texts.get(key)
            if text:
                platforms_to_check[platform] = text

        if platforms_to_check:
            user_prompt = f"ОРИГИНАЛЬНЫЙ ТРАНСКРИПТ:\n{truncated}\n\nТЕКСТЫ ДЛЯ ПРОВЕРКИ:\n"
            for platform, text in platforms_to_check.items():
                user_prompt += f"=== {platform} ===\n{text}\n\n"

            result = self.llm.complete_json(
                VALIDATOR_SYSTEM_PROMPT,
                user_prompt,
                settings.validation_model,
            )

            for platform in platforms_to_check.keys():
                platform_result = result.get(platform, {"checks": [{"name": "error", "passed": False, "details": "Validation failed to return result for this platform"}]})
                report[platform] = platform_result
                checks = platform_result.get("checks", [])
                if any(not c.get("passed", False) for c in checks):
                    all_passed = False

        banana = texts.get("banana_video_prompt")
        if banana is not None and (target_keys is None or "banana_video_prompt" in target_keys):
            banana_report = self._validate_banana_format(banana)
            report["banana_video_prompt"] = banana_report
            if not banana_report["passed"]:
                all_passed = False

        overall_verdict = "approved" if all_passed else "needs_revision"
        logger.info("Validation verdict: %s", overall_verdict)

        return {
            "overall_verdict": overall_verdict,
            "report_json": report,
        }

    @staticmethod
    def _validate_banana_format(data: dict) -> dict:
        errors: list[str] = []

        if not isinstance(data.get("style_summary"), str):
            errors.append("missing or invalid 'style_summary' (expected string)")

        scenes = data.get("scenes")
        if not isinstance(scenes, list) or len(scenes) == 0:
            errors.append("missing or empty 'scenes' array")
        else:
            for i, scene in enumerate(scenes):
                if not isinstance(scene, dict):
                    errors.append(f"scene {i}: not an object")
                    continue
                missing = SCENE_REQUIRED_KEYS - set(scene.keys())
                if missing:
                    errors.append(f"scene {i}: missing keys {missing}")

        return {
            "passed": len(errors) == 0,
            "details": "; ".join(errors) if errors else "Valid banana_video_prompt format",
        }
