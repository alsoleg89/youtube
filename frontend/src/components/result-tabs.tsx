"use client";

import { useState } from "react";
import { CopyButton } from "./copy-button";
import type { ResultInfo } from "@/types/video";

interface ResultTabsProps {
  result: ResultInfo;
}

const TABS = [
  { key: "medium_text" as const, label: "Medium" },
  { key: "habr_text" as const, label: "Habr" },
  { key: "linkedin_text" as const, label: "LinkedIn" },
] as const;

export function ResultTabs({ result }: ResultTabsProps) {
  const availableTabs = TABS.filter((tab) => result[tab.key]);
  const [activeKey, setActiveKey] = useState(availableTabs[0]?.key ?? "medium_text");

  const activeText = result[activeKey] ?? "";

  if (availableTabs.length === 0) {
    return (
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-8 text-center text-zinc-500">
        Нет доступных текстов
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/80 overflow-hidden backdrop-blur-sm">
      <div className="flex border-b border-zinc-800">
        {availableTabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveKey(tab.key)}
            className={`
              relative flex-1 px-6 py-4 text-sm font-medium transition-colors duration-200
              ${
                activeKey === tab.key
                  ? "text-white"
                  : "text-zinc-500 hover:text-zinc-300"
              }
            `}
          >
            {tab.label}
            {activeKey === tab.key && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-indigo-500 to-purple-500" />
            )}
          </button>
        ))}
      </div>

      <div className="p-6 sm:p-8">
        <div className="mb-4 flex justify-end">
          <CopyButton text={activeText} />
        </div>
        <div className="max-h-[60vh] overflow-y-auto rounded-xl bg-zinc-800/50 p-6 ring-1 ring-zinc-700/50">
          <pre className="whitespace-pre-wrap break-words font-sans text-sm leading-relaxed text-zinc-300">
            {activeText}
          </pre>
        </div>
      </div>
    </div>
  );
}
