"use client";

import { useState } from "react";
import { CopyButton } from "./copy-button";
import { CHANNEL_LABELS, HIDDEN_PAYLOAD_KEYS } from "@/lib/constants";

interface ChannelTabsProps {
  contentPayload: Record<string, unknown>;
}

export function ChannelTabs({ contentPayload }: ChannelTabsProps) {
  const channelKeys = Object.keys(contentPayload).filter(
    (k) => !HIDDEN_PAYLOAD_KEYS.has(k),
  );

  const [activeKey, setActiveKey] = useState(channelKeys[0] ?? "");

  if (channelKeys.length === 0) {
    return (
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/80 p-8 text-center text-zinc-500">
        Нет доступных текстов
      </div>
    );
  }

  const activeValue = contentPayload[activeKey];
  const isJson = typeof activeValue === "object" && activeValue !== null;
  const displayText = isJson
    ? JSON.stringify(activeValue, null, 2)
    : String(activeValue ?? "");

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/80 overflow-hidden backdrop-blur-sm">
      <div className="flex border-b border-zinc-800 overflow-x-auto">
        {channelKeys.map((key) => (
          <button
            key={key}
            onClick={() => setActiveKey(key)}
            className={`
              relative flex-shrink-0 px-6 py-4 text-sm font-medium transition-colors duration-200
              ${
                activeKey === key
                  ? "text-white"
                  : "text-zinc-500 hover:text-zinc-300"
              }
            `}
          >
            {CHANNEL_LABELS[key] ?? key}
            {activeKey === key && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-indigo-500 to-purple-500" />
            )}
          </button>
        ))}
      </div>

      <div className="p-6 sm:p-8">
        <div className="mb-4 flex justify-end">
          <CopyButton text={displayText} />
        </div>
        <div className="max-h-[60vh] overflow-y-auto rounded-xl bg-zinc-800/50 p-6 ring-1 ring-zinc-700/50">
          <pre className="whitespace-pre-wrap break-words font-sans text-sm leading-relaxed text-zinc-300">
            {displayText}
          </pre>
        </div>
      </div>
    </div>
  );
}
