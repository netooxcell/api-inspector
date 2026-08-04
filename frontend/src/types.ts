export type Severity = "success" | "warning" | "error" | "pending";

export type StatusFilter = "all" | "success" | "error" | "warning";

export interface DetectedIssue {
  field: string;
  issue: string;
}

export interface CapturedRequest {
  id: number;
  parent_id: number | null;
  method: string;
  target_url: string;
  req_headers: Record<string, string>;
  req_body: unknown;
  req_params: Record<string, string>;
  res_status: number | null;
  res_headers: Record<string, string>;
  res_body: unknown;
  duration_ms: number | null;
  severity: Severity;
  summary: string | null;
  error_code: string | null;
  explanation: string | null;
  suggestion: string | null;
  detected_issues: DetectedIssue[];
  timestamp: string;
}

export interface ProxyPayload {
  target_url: string;
  method: string;
  headers?: Record<string, string>;
  body?: unknown;
  query_params?: Record<string, string>;
}

export interface ReplayPayload {
  target_url?: string;
  headers?: Record<string, string>;
  body?: unknown;
  query_params?: Record<string, string>;
}

export interface WsMessage {
  type: "request_completed";
  data: CapturedRequest;
}
