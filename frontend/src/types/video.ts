export interface ProgressInfo {
  stage: string;
  percent: number;
}

export interface ErrorInfo {
  code: string;
  message: string;
}

export interface ResultInfo {
  medium_text?: string;
  habr_text?: string;
  linkedin_text?: string;
  validation_report?: Record<string, unknown>;
}

export type VideoStatus =
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

export interface VideoResponse {
  video_id: string;
  status: VideoStatus;
  progress: ProgressInfo | null;
  error: ErrorInfo | null;
  result: ResultInfo | null;
}

export interface CreateVideoResponse {
  video_id: string;
  status: "queued";
}

export interface RegenerateVideoResponse {
  video_id: string;
  status: string;
}
