"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { listSources } from "@/lib/api-client";
import type { SourceListItem } from "@/types/video";

const SOURCE_TYPE_ICONS: Record<string, { icon: React.ReactNode; color: string }> = {
  youtube: {
    icon: (
      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
        <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
      </svg>
    ),
    color: "text-red-500",
  },
  web: {
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
      </svg>
    ),
    color: "text-indigo-400",
  },
  pdf: {
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
      </svg>
    ),
    color: "text-orange-400",
  },
  epub: {
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
      </svg>
    ),
    color: "text-emerald-400",
  },
};

const STATUS_STYLES: Record<string, { label: string; bg: string; text: string }> = {
  approved: { label: "Готово", bg: "bg-emerald-500/15", text: "text-emerald-400" },
  needs_review: { label: "На проверке", bg: "bg-amber-500/15", text: "text-amber-400" },
  failed: { label: "Ошибка", bg: "bg-red-500/15", text: "text-red-400" },
};

function getStatusStyle(status: string) {
  return STATUS_STYLES[status] ?? { label: "В работе", bg: "bg-indigo-500/15", text: "text-indigo-400" };
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function HistoryFeed() {
  const [items, setItems] = useState<SourceListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    listSources(20, 0)
      .then((res) => setItems(res.items))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return null;
  }

  if (items.length === 0) {
    return null;
  }

  return (
    <div className="w-full max-w-2xl mx-auto mt-12">
      <h2 className="text-lg font-semibold text-zinc-400 mb-4">
        Прошлые запросы
      </h2>
      <div className="space-y-2">
        {items.map((item) => {
          const typeInfo = SOURCE_TYPE_ICONS[item.source_type] ?? SOURCE_TYPE_ICONS.web;
          const status = getStatusStyle(item.status);

          return (
            <button
              key={item.source_id}
              onClick={() => router.push(`/sources/${item.source_id}`)}
              className="
                w-full flex items-center gap-4 rounded-xl border border-zinc-800
                bg-zinc-900/80 px-4 py-3 text-left
                transition-all duration-200
                hover:border-zinc-600 hover:bg-zinc-800/80
                active:scale-[0.99]
              "
            >
              <div className={`flex shrink-0 items-center justify-center rounded-lg bg-zinc-800 p-2 ${typeInfo.color}`}>
                {typeInfo.icon}
              </div>

              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-zinc-200 truncate">
                  {item.title || "Без названия"}
                </p>
                <p className="text-xs text-zinc-500 mt-0.5">
                  {formatDate(item.created_at)}
                </p>
              </div>

              <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${status.bg} ${status.text}`}>
                {status.label}
              </span>

              <svg className="h-4 w-4 shrink-0 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
            </button>
          );
        })}
      </div>
    </div>
  );
}
