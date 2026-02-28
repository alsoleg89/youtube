"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getSource } from "./api-client";
import { TERMINAL_STATUSES } from "./constants";
import type { SourceResponse } from "@/types/video";

const BASE_INTERVAL = 3000;
const MAX_INTERVAL = 15000;

function getInterval(attempts: number): number {
  return Math.min(BASE_INTERVAL * Math.pow(1.5, Math.floor(attempts / 3)), MAX_INTERVAL);
}

export function useSourcePolling(sourceId: string | null) {
  const [source, setSource] = useState<SourceResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const attemptsRef = useRef(0);
  const activeRef = useRef(false);

  const stopPolling = useCallback(() => {
    activeRef.current = false;
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setIsPolling(false);
  }, []);

  const scheduleNext = useCallback(
    (id: string) => {
      if (!activeRef.current) return;
      const delay = getInterval(attemptsRef.current);
      timerRef.current = setTimeout(() => fetchSource(id), delay);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const fetchSource = useCallback(
    async (id: string) => {
      try {
        const data = await getSource(id);
        setSource(data);
        setError(null);
        attemptsRef.current += 1;

        if (
          TERMINAL_STATUSES.includes(
            data.status as (typeof TERMINAL_STATUSES)[number],
          )
        ) {
          stopPolling();
        } else {
          scheduleNext(id);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Произошла ошибка");
        stopPolling();
      }
    },
    [stopPolling, scheduleNext],
  );

  useEffect(() => {
    if (!sourceId) {
      stopPolling();
      return;
    }

    activeRef.current = true;
    attemptsRef.current = 0;
    setIsPolling(true);
    fetchSource(sourceId);

    return stopPolling;
  }, [sourceId, fetchSource, stopPolling]);

  return { source, error, isPolling };
}
