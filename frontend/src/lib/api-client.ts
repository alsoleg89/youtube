import { API_BASE } from "./constants";
import type {
  CreateVideoResponse,
  RegenerateVideoResponse,
  VideoResponse,
} from "@/types/video";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(body || `Request failed with status ${res.status}`);
  }

  return res.json();
}

export async function createVideo(url: string): Promise<CreateVideoResponse> {
  return request<CreateVideoResponse>("/api/videos", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export async function getVideo(id: string): Promise<VideoResponse> {
  return request<VideoResponse>(`/api/videos/${id}`);
}

export async function regenerateVideo(
  id: string,
): Promise<RegenerateVideoResponse> {
  return request<RegenerateVideoResponse>(`/api/videos/${id}/regenerate`, {
    method: "POST",
  });
}
