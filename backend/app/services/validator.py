import logging
from abc import ABC, abstractmethod

from app.core.config import settings
from app.providers.base_llm import BaseLLMProvider

logger = logging.getLogger(__name__)

VALIDATOR_SYSTEM_PROMPT = (
    "Ты — строгий редактор. Проверь предоставленный текст, написанный для "
    "платформы {platform}, по трём критериям.\n\n"
    "Для каждого критерия определи, пройдена ли проверка (passed: true/false), "
    "и дай краткое пояснение (details).\n\n"
    "Критерии:\n"
    "1. policy_risk — содержит ли текст потенциально опасный, незаконный, "
    "оскорбительный или неэтичный контент?\n"
    "2. hallucination — есть ли в тексте факты, цифры или утверждения, "
    "которых НЕТ в оригинальном транскрипте? Сравнивай дословно.\n"
    "3. tone_mismatch — соответствует ли тон и стиль текста целевой "
    "платформе ({platform})?\n\n"
    'Ответ строго в формате JSON:\n'
    '{{\n'
    '  "checks": [\n'
    '    {{"name": "policy_risk", "passed": true, "details": "..."}},\n'
    '    {{"name": "hallucination", "passed": true, "details": "..."}},\n'
    '    {{"name": "tone_mismatch", "passed": true, "details": "..."}}\n'
    "  ]\n"
    "}}"
)


class BaseValidatorService(ABC):
    @abstractmethod
    def validate(self, texts: dict, transcript: str) -> dict: ...


class ValidatorService(BaseValidatorService):
    def __init__(self, llm: BaseLLMProvider) -> None:
        self.llm = llm

    def validate(self, texts: dict, transcript: str) -> dict:
        report: dict = {}
        all_passed = True

        for platform in ("medium", "habr", "linkedin"):
            text = texts[f"{platform}_text"]
            user_prompt = (
                f"ТЕКСТ ДЛЯ ПРОВЕРКИ:\n{text}\n\n"
                f"ОРИГИНАЛЬНЫЙ ТРАНСКРИПТ:\n{transcript}"
            )
            result = self.llm.complete_json(
                VALIDATOR_SYSTEM_PROMPT.format(platform=platform),
                user_prompt,
                settings.validation_model,
            )
            report[platform] = result

            checks = result.get("checks", [])
            if any(not c.get("passed", False) for c in checks):
                all_passed = False

        overall_verdict = "approved" if all_passed else "needs_revision"
        logger.info("Validation verdict: %s", overall_verdict)

        return {
            "overall_verdict": overall_verdict,
            "report_json": report,
        }
