"use client";

import { type FormEvent, useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createSource, uploadSource } from "@/lib/api-client";
import type { SourceType } from "@/types/video";

const YOUTUBE_REGEX =
  /^(https?:\/\/)?(www\.)?(youtube\.com\/(watch\?v=|embed\/|shorts\/)|youtu\.be\/).+/;
const WEB_URL_REGEX = /^https?:\/\/.+/;

type InputMode = "url" | "file";

export function SourceForm() {
  const [mode, setMode] = useState<InputMode>("url");
  const [sourceType, setSourceType] = useState<SourceType>("youtube");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const handleModeChange = useCallback((newType: SourceType) => {
    setSourceType(newType);
    setError(null);
    if (newType === "pdf" || newType === "epub") {
      setMode("file");
    } else {
      setMode("url");
    }
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (mode === "url") {
      if (!url.trim()) {
        setError("Вставьте ссылку");
        return;
      }
      if (sourceType === "youtube" && !YOUTUBE_REGEX.test(url.trim())) {
        setError("Некорректная ссылка на YouTube видео");
        return;
      }
      if (sourceType === "web" && !WEB_URL_REGEX.test(url.trim())) {
        setError("Ссылка должна начинаться с http:// или https://");
        return;
      }

      setLoading(true);
      try {
        const { source_id } = await createSource(url.trim(), sourceType);
        router.push(`/sources/${source_id}`);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Не удалось отправить источник",
        );
        setLoading(false);
      }
    } else {
      if (!file) {
        setError("Выберите файл");
        return;
      }

      setLoading(true);
      try {
        const { source_id } = await uploadSource(file);
        router.push(`/sources/${source_id}`);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Не удалось загрузить файл",
        );
        setLoading(false);
      }
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) {
      setFile(dropped);
      setError(null);
    }
  };

  const SOURCE_TYPES: { value: SourceType; label: string }[] = [
    { value: "youtube", label: "YouTube" },
    { value: "web", label: "Веб-статья" },
    { value: "pdf", label: "PDF" },
    { value: "epub", label: "EPUB" },
  ];

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-6 sm:p-8 shadow-2xl shadow-black/20 backdrop-blur-sm">
        {/* Source type selector */}
        <div className="flex gap-2 mb-6">
          {SOURCE_TYPES.map((st) => (
            <button
              key={st.value}
              type="button"
              onClick={() => handleModeChange(st.value)}
              className={`
                flex-1 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200
                ${
                  sourceType === st.value
                    ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/25"
                    : "bg-zinc-800 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700"
                }
              `}
            >
              {st.label}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {mode === "url" ? (
            <div className="relative">
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4">
                {sourceType === "youtube" ? (
                  <svg
                    className="h-5 w-5 text-red-500"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                  >
                    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
                  </svg>
                ) : (
                  <svg
                    className="h-5 w-5 text-indigo-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
                    />
                  </svg>
                )}
              </div>
              <input
                type="url"
                value={url}
                onChange={(e) => {
                  setUrl(e.target.value);
                  setError(null);
                }}
                placeholder={
                  sourceType === "youtube"
                    ? "https://www.youtube.com/watch?v=..."
                    : "https://example.com/article..."
                }
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
          ) : (
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`
                flex flex-col items-center justify-center rounded-xl border-2 border-dashed
                py-10 px-6 cursor-pointer transition-all duration-200
                ${
                  dragOver
                    ? "border-indigo-500 bg-indigo-500/10"
                    : "border-zinc-700 bg-zinc-800/50 hover:border-zinc-500"
                }
              `}
            >
              <svg
                className="h-10 w-10 text-zinc-500 mb-3"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
                />
              </svg>
              {file ? (
                <p className="text-sm text-zinc-300">
                  {file.name}{" "}
                  <span className="text-zinc-500">
                    ({(file.size / 1024 / 1024).toFixed(1)} MB)
                  </span>
                </p>
              ) : (
                <p className="text-sm text-zinc-500">
                  Перетащите {sourceType.toUpperCase()} файл сюда или нажмите
                  для выбора
                </p>
              )}
              <p className="text-xs text-zinc-600 mt-1">Максимум 10 MB</p>
              <input
                ref={fileInputRef}
                type="file"
                accept={sourceType === "pdf" ? ".pdf" : ".epub"}
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) {
                    setFile(f);
                    setError(null);
                  }
                }}
              />
            </div>
          )}

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
              "Конвертировать"
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
