export const TERMINAL_STATUSES = ["approved", "needs_review", "failed"] as const;

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const STAGE_LABELS: Record<string, string> = {
  queued: "В очереди",
  extracting: "Извлечение",
  transcribing: "Транскрибирование",
  chunking: "Разбивка на фрагменты",
  mapping: "Анализ фрагментов",
  reducing: "Генерация текстов",
  validating: "Валидация",
  done: "Готово",
  failed: "Ошибка",
};

export const CHANNEL_LABELS: Record<string, string> = {
  medium_text: "Medium",
  habr_text: "Habr",
  linkedin_text: "LinkedIn",
  research_article: "ResearchGate",
  banana_video_prompt: "Видео-промпт",
};

export const HIDDEN_PAYLOAD_KEYS = new Set([
  "reduce_summary_text",
]);
