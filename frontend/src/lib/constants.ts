export const POLL_INTERVAL = 3000;

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
