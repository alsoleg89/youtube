import { API_BASE } from "./constants";
import type {
  CreateSourceResponse,
  RegenerateResponse,
  SourceListResponse,
  SourceResponse,
  SourceType,
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

export async function createSource(
  url: string,
  sourceType: SourceType = "youtube",
): Promise<CreateSourceResponse> {
  return request<CreateSourceResponse>("/api/sources", {
    method: "POST",
    body: JSON.stringify({ url, source_type: sourceType }),
  });
}

export async function uploadSource(
  file: File,
): Promise<CreateSourceResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/api/sources/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(body || `Upload failed with status ${res.status}`);
  }

  return res.json();
}

export async function getSource(id: string): Promise<SourceResponse> {
  return request<SourceResponse>(`/api/sources/${id}`);
}

export async function regenerateSource(
  id: string,
): Promise<RegenerateResponse> {
  return request<RegenerateResponse>(`/api/sources/${id}/regenerate`, {
    method: "POST",
  });
}

export async function listSources(
  limit = 20,
  offset = 0,
): Promise<SourceListResponse> {
  return request<SourceListResponse>(
    `/api/sources?limit=${limit}&offset=${offset}`,
  );
}
