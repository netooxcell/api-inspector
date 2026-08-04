import { CheckCircle2, Clock, Repeat, XCircle } from "lucide-react";
import type { CapturedRequest, StatusFilter } from "../types";
import { formatTime, hostFromUrl } from "../utils";

const FILTERS: { key: StatusFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "success", label: "Success" },
  { key: "warning", label: "Warning" },
  { key: "error", label: "Error" },
];

function FeedIcon({ severity }: { severity: CapturedRequest["severity"] }) {
  if (severity === "pending") return <Clock size={14} className="feed-item-icon pending" />;
  if (severity === "success") return <CheckCircle2 size={14} className="feed-item-icon success" />;
  if (severity === "warning") return <XCircle size={14} className="feed-item-icon warning" />;
  return <XCircle size={14} className="feed-item-icon error" />;
}

export default function RequestFeed({
  requests,
  selectedId,
  onSelect,
  filter,
  onFilterChange,
}: {
  requests: CapturedRequest[];
  selectedId: number | null;
  onSelect: (r: CapturedRequest) => void;
  filter: StatusFilter;
  onFilterChange: (f: StatusFilter) => void;
}) {
  return (
    <div className="feed-panel">
      <div className="feed-toolbar">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            className={`filter-btn ${filter === f.key ? "active" : ""}`}
            onClick={() => onFilterChange(f.key)}
          >
            {f.label}
          </button>
        ))}
      </div>
      <div className="feed-list">
        {requests.length === 0 && <div className="feed-empty">No requests captured yet</div>}
        {requests.map((r) => (
          <button
            key={r.id}
            className={`feed-item ${selectedId === r.id ? "selected" : ""}`}
            onClick={() => onSelect(r)}
          >
            <FeedIcon severity={r.severity} />
            <div className="feed-item-body">
              <div className="feed-item-row1">
                <span className="feed-item-time">{formatTime(r.timestamp)}</span>
                <span className="feed-item-method">{r.method}</span>
                <span className="feed-item-status">{r.res_status ?? (r.severity === "pending" ? "…" : "ERR")}</span>
                {r.parent_id && (
                  <span className="feed-item-replay-tag">
                    <Repeat size={10} style={{ verticalAlign: "middle" }} /> replay
                  </span>
                )}
              </div>
              <div className="feed-item-host">{hostFromUrl(r.target_url)}</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
