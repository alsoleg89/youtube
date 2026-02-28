"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { createVideo } from "@/lib/api-client";

const YOUTUBE_REGEX =
  /^(https?:\/\/)?(www\.)?(youtube\.com\/(watch\?v=|embed\/|shorts\/)|youtu\.be\/).+/;

export function URLForm() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!url.trim()) {
      setError("Вставьте ссылку на видео");
      return;
    }

    if (!YOUTUBE_REGEX.test(url.trim())) {
      setError("Некорректная ссылка на YouTube видео");
      return;
    }

    setLoading(true);
    try {
      const { video_id } = await createVideo(url.trim());
      router.push(`/videos/${video_id}`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Не удалось отправить видео",
      );
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-6 sm:p-8 shadow-2xl shadow-black/20 backdrop-blur-sm">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="relative">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4">
              <svg
                className="h-5 w-5 text-red-500"
                viewBox="0 0 24 24"
                fill="currentColor"
              >
                <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
              </svg>
            </div>
            <input
              type="url"
              value={url}
              onChange={(e) => {
                setUrl(e.target.value);
                setError(null);
              }}
              placeholder="https://www.youtube.com/watch?v=..."
              disabled={loading}
              className="
                w-full rounded-xl border border-zinc-700 bg-zinc-800/50
                py-4 pl-12 pr-4 text-zinc-100 placeholder-zinc-500
                outline-none transition-all duration-200
                focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20
                disabled:opacity-50
              "
            />
          </div>

          {error && (
            <p className="text-sm text-red-400 px-1 animate-in fade-in">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="
              relative w-full rounded-xl py-4 font-semibold text-white
              bg-gradient-to-r from-indigo-600 to-purple-600
              transition-all duration-200
              hover:from-indigo-500 hover:to-purple-500 hover:shadow-lg hover:shadow-indigo-500/25
              active:scale-[0.98]
              disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none
            "
          >
            {loading ? (
              <span className="inline-flex items-center gap-2">
                <svg
                  className="h-5 w-5 animate-spin"
                  viewBox="0 0 24 24"
                  fill="none"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                Отправка…
              </span>
            ) : (
              "Конвертировать в статью"
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
