import { useState } from "react";
import { Inbox } from "lucide-react";
import type { CapturedRequest } from "../types";
import { durationBadgeClass, statusBadgeClass } from "../utils";
import RequestTab from "./RequestTab";
import ResponseTab from "./ResponseTab";
import AnalysisTab from "./AnalysisTab";

type Tab = "request" | "response" | "analysis";

export default function DetailPanel({
  request,
  onReplay,
}: {
  request: CapturedRequest | null;
  onReplay: (request: CapturedRequest) => void;
}) {
  const [tab, setTab] = useState<Tab>("request");

  if (!request) {
    return (
      <div className="detail-panel">
        <div className="detail-empty">
          <Inbox size={28} />
          <span>Select a request to inspect it</span>
        </div>
      </div>
    );
  }

  const statusCls = statusBadgeClass(request.res_status);

  return (
    <div className="detail-panel">
      <div className="detail-header">
        <div className="detail-header-badges">
          <span className="badge badge-neutral">{request.method}</span>
          {request.severity === "pending" ? (
            <span className="badge badge-pending">PENDING…</span>
          ) : (
            <span className={`badge ${statusCls}`}>{request.res_status ?? "—"}</span>
          )}
          {request.error_code && <span className="badge badge-neutral">{request.error_code}</span>}
          {request.duration_ms !== null && (
            <span className={`duration-badge ${durationBadgeClass(request.duration_ms)}`}>
              {request.duration_ms}ms
            </span>
          )}
        </div>
        <div className="detail-url">{request.target_url}</div>
        <div className="detail-meta">
          <span>#{request.id}</span>
          {request.parent_id && <span>replay of #{request.parent_id}</span>}
        </div>
      </div>

      <div className="tabs">
        <button className={`tab-btn ${tab === "request" ? "active" : ""}`} onClick={() => setTab("request")}>
          Request
        </button>
        <button className={`tab-btn ${tab === "response" ? "active" : ""}`} onClick={() => setTab("response")}>
          Response
        </button>
        <button className={`tab-btn ${tab === "analysis" ? "active" : ""}`} onClick={() => setTab("analysis")}>
          Analysis
        </button>
      </div>

      <div className="tab-content">
        {tab === "request" && <RequestTab request={request} />}
        {tab === "response" && <ResponseTab request={request} />}
        {tab === "analysis" && <AnalysisTab request={request} onReplay={() => onReplay(request)} />}
      </div>
    </div>
  );
}
