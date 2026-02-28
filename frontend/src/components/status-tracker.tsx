"use client";

import { useState } from "react";
import { regenerateSource } from "@/lib/api-client";
import { CHANNEL_LABELS, STAGE_LABELS } from "@/lib/constants";
import type { SourceResponse } from "@/types/video";

const PLATFORM_TO_PAYLOAD: Record<string, string> = {
  medium: "medium_text",
  habr: "habr_text",
  linkedin: "linkedin_text",
  research_article: "research_article",
  banana_video_prompt: "banana_video_prompt",
};

function getFailedChannels(
  report: Record<string, unknown> | null,
): { key: string; label: string; reason: string }[] {
  if (!report) return [];
  const failed: { key: string; label: string; reason: string }[] = [];

  for (const [platform, entry] of Object.entries(report)) {
    const e = entry as Record<string, unknown>;
    const payloadKey = PLATFORM_TO_PAYLOAD[platform] ?? platform;
    const label = CHANNEL_LABELS[payloadKey] ?? platform;

    if (Array.isArray(e?.checks)) {
      const failedChecks = (e.checks as { name: string; passed: boolean; details: string }[])
        .filter((c) => !c.passed);
      if (failedChecks.length > 0) {
        const reason = failedChecks.map((c) => c.name.replace("_", " ")).join(", ");
        failed.push({ key: payloadKey, label, reason });
      }
    } else if (e?.passed === false) {
      failed.push({ key: payloadKey, label, reason: String(e.details ?? "формат") });
    }
  }
  return failed;
}

interface StatusTrackerProps {
  source: SourceResponse;
  onRegenerate?: () => void;
}

export function StatusTracker({ source, onRegenerate }: StatusTrackerProps) {
  const [regenerating, setRegenerating] = useState(false);

  const stageLabel =
    STAGE_LABELS[source.progress?.stage ?? source.status] ??
    source.progress?.stage ??
    source.status;

  const percent = source.progress?.percent ?? 0;

  const handleRegenerate = async () => {
    setRegenerating(true);
    try {
      await regenerateSource(source.source_id);
      onRegenerate?.();
    } catch {
      setRegenerating(false);
    }
  };

  if (source.status === "failed") {
    return (
      <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-6 sm:p-8">
        <div className="flex items-start gap-4">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-500/20">
            <svg className="h-5 w-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <div className="min-w-0">
            <h3 className="text-lg font-semibold text-red-400">Ошибка обработки</h3>
            {source.error && (
              <p className="mt-2 text-sm text-red-300/80">
                {source.error.message}
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (source.status === "needs_review") {
    const failedChannels = getFailedChannels(source.validation_report);

    return (
      <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-6 sm:p-8">
        <div className="flex flex-col gap-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-amber-500/20">
                <svg className="h-5 w-5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-amber-400">
                  Частичная проверка
                </h3>
                <p className="mt-1 text-sm text-amber-300/70">
                  {failedChannels.length > 0
                    ? `Не прошли: ${failedChannels.map((c) => c.label).join(", ")}`
                    : "Результат не прошёл валидацию"}
                </p>
              </div>
            </div>
            <button
              onClick={handleRegenerate}
              disabled={regenerating}
              className="
                shrink-0 rounded-xl px-6 py-3 font-semibold text-white
                bg-gradient-to-r from-amber-600 to-orange-600
                transition-all duration-200
                hover:from-amber-500 hover:to-orange-500 hover:shadow-lg hover:shadow-amber-500/25
                active:scale-[0.98]
                disabled:opacity-50 disabled:cursor-not-allowed
              "
            >
              {regenerating ? "Перезапуск…" : "Перегенерировать"}
            </button>
          </div>

          {failedChannels.length > 0 && (
            <div className="flex flex-wrap gap-2 ml-14">
              {failedChannels.map((ch) => (
                <span
                  key={ch.key}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-amber-500/15 px-3 py-1.5 text-xs text-amber-300"
                >
                  <span className="font-medium">{ch.label}</span>
                  <span className="text-amber-400/60">{ch.reason}</span>
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-6 sm:p-8 backdrop-blur-sm">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="relative flex h-3 w-3">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-indigo-400 opacity-75" />
            <span className="relative inline-flex h-3 w-3 rounded-full bg-indigo-500" />
          </div>
          <span className="text-lg font-medium text-zinc-200">
            {stageLabel}
          </span>
        </div>
        <span className="text-sm font-mono text-zinc-400">{percent}%</span>
      </div>

      <div className="h-3 w-full overflow-hidden rounded-full bg-zinc-800">
        <div
          className="h-full rounded-full bg-gradient-to-r from-indigo-600 to-purple-500 transition-all duration-700 ease-out"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
