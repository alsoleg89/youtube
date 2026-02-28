export interface ProgressInfo {
  stage: string;
  percent: number;
}

export interface ErrorInfo {
  code: string;
  message: string;
}

export type SourceType = "youtube" | "pdf" | "epub" | "web";

export type SourceStatus =
  | "queued"
  | "extracting"
  | "transcribing"
  | "chunking"
  | "mapping"
  | "reducing"
  | "validating"
  | "approved"
  | "needs_review"
  | "failed";

export interface SourceResponse {
  source_id: string;
  source_type: SourceType;
  status: SourceStatus;
  progress: ProgressInfo | null;
  error: ErrorInfo | null;
  content_payload: Record<string, unknown> | null;
  validation_report: Record<string, unknown> | null;
}

export interface CreateSourceResponse {
  source_id: string;
  source_type: SourceType;
  status: "queued";
}

export interface RegenerateResponse {
  source_id: string;
  status: string;
}

export interface SourceListItem {
  source_id: string;
  title: string | null;
  source_type: SourceType;
  status: SourceStatus;
  created_at: string;
}

export interface SourceListResponse {
  items: SourceListItem[];
  total: number;
}
