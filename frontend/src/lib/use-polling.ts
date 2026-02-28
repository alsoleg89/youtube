"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getVideo } from "./api-client";
import { POLL_INTERVAL, TERMINAL_STATUSES } from "./constants";
import type { VideoResponse } from "@/types/video";

export function useVideoPolling(videoId: string | null) {
  const [video, setVideo] = useState<VideoResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsPolling(false);
  }, []);

  const fetchVideo = useCallback(
    async (id: string) => {
      try {
        const data = await getVideo(id);
        setVideo(data);
        setError(null);

        if (
          TERMINAL_STATUSES.includes(
            data.status as (typeof TERMINAL_STATUSES)[number],
          )
        ) {
          stopPolling();
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Произошла ошибка");
        stopPolling();
      }
    },
    [stopPolling],
  );

  useEffect(() => {
    if (!videoId) {
      stopPolling();
      return;
    }

    setIsPolling(true);
    fetchVideo(videoId);

    intervalRef.current = setInterval(() => {
      fetchVideo(videoId);
    }, POLL_INTERVAL);

    return stopPolling;
  }, [videoId, fetchVideo, stopPolling]);

  return { video, error, isPolling };
}
