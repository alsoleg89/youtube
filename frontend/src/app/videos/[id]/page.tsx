"use client";

import { use } from "react";
import Link from "next/link";
import { useVideoPolling } from "@/lib/use-polling";
import { StatusTracker } from "@/components/status-tracker";
import { ResultTabs } from "@/components/result-tabs";

export default function VideoPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { video, error, isPolling } = useVideoPolling(id);

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
            Обработка видео
          </span>
        </h1>

        {error && !video && (
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

        {!video && !error && (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-zinc-700 border-t-indigo-500" />
            <p className="mt-4 text-zinc-500">Загрузка…</p>
          </div>
        )}

        {video && (
          <div className="space-y-8">
            {video.status !== "approved" && (
              <StatusTracker
                video={video}
                onRegenerate={() => window.location.reload()}
              />
            )}

            {video.status === "approved" && video.result && (
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
                <ResultTabs result={video.result} />
              </>
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
