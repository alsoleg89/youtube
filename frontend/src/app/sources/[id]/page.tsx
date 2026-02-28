"use client";

import Link from "next/link";
import { useSourcePolling } from "@/lib/use-polling";
import { StatusTracker } from "@/components/status-tracker";
import { ChannelTabs } from "@/components/result-tabs";
import { HIDDEN_PAYLOAD_KEYS } from "@/lib/constants";

const PLATFORM_TO_PAYLOAD: Record<string, string> = {
  medium: "medium_text",
  habr: "habr_text",
  linkedin: "linkedin_text",
  research_article: "research_article",
  banana_video_prompt: "banana_video_prompt",
};

function getPassedPayload(
  payload: Record<string, unknown>,
  report: Record<string, unknown>,
): Record<string, unknown> {
  const failedKeys = new Set<string>();

  for (const [platform, entry] of Object.entries(report)) {
    const e = entry as Record<string, unknown>;
    const payloadKey = PLATFORM_TO_PAYLOAD[platform] ?? platform;

    if (Array.isArray(e?.checks)) {
      if ((e.checks as { passed: boolean }[]).some((c) => !c.passed)) {
        failedKeys.add(payloadKey);
      }
    } else if (e?.passed === false) {
      failedKeys.add(payloadKey);
    }
  }

  const passed: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(payload)) {
    if (!failedKeys.has(k) && !HIDDEN_PAYLOAD_KEYS.has(k)) {
      passed[k] = v;
    }
  }
  return passed;
}

export default function SourcePage({
  params,
}: {
  params: { id: string };
}) {
  const { id } = params;
  const { source, error, isPolling } = useSourcePolling(id);

  const passedPayload =
    source?.status === "needs_review" &&
    source.content_payload &&
    source.validation_report
      ? getPassedPayload(source.content_payload, source.validation_report)
      : null;

  return (
    <main className="min-h-screen px-4 py-8 sm:py-12">
      <div className="mx-auto max-w-3xl">
        <Link
          href="/"
          className="
            inline-flex items-center gap-2 text-sm text-zinc-500
            transition-colors duration-200 hover:text-zinc-300 mb-8
          "
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          Назад
        </Link>

        <h1 className="text-3xl sm:text-4xl font-bold mb-8">
          <span className="bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
            Обработка источника
          </span>
        </h1>

        {error && !source && (
          <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-6 sm:p-8">
            <div className="flex items-start gap-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-500/20">
                <svg className="h-5 w-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-red-400">Ошибка</h3>
                <p className="mt-2 text-sm text-red-300/80">{error}</p>
              </div>
            </div>
          </div>
        )}

        {!source && !error && (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-zinc-700 border-t-indigo-500" />
            <p className="mt-4 text-zinc-500">Загрузка…</p>
          </div>
        )}

        {source && (
          <div className="space-y-8">
            {source.status !== "approved" && (
              <StatusTracker
                source={source}
                onRegenerate={() => window.location.reload()}
              />
            )}

            {source.status === "approved" && source.content_payload && (
              <>
                <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-6">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-emerald-500/20">
                      <svg className="h-5 w-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                    <h3 className="text-lg font-semibold text-emerald-400">
                      Готово
                    </h3>
                  </div>
                </div>
                <ChannelTabs contentPayload={source.content_payload} />
              </>
            )}

            {passedPayload && Object.keys(passedPayload).length > 0 && (
              <ChannelTabs contentPayload={passedPayload} />
            )}

            {isPolling && (
              <p className="text-center text-sm text-zinc-600">
                Автообновление каждые 3 секунды
              </p>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
