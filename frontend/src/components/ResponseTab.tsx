import type { CapturedRequest } from "../types";
import { durationBadgeClass, statusBadgeClass, tryFormatBody } from "../utils";
import KeyValueTable from "./KeyValueTable";
import JsonView from "./JsonView";

const STATUS_TEXT: Record<number, string> = {
  200: "OK", 201: "Created", 202: "Accepted", 204: "No Content",
  301: "Moved Permanently", 302: "Found",
  400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found",
  422: "Unprocessable Entity", 429: "Too Many Requests",
  500: "Internal Server Error", 502: "Bad Gateway", 503: "Service Unavailable", 504: "Gateway Timeout",
};

export default function ResponseTab({ request }: { request: CapturedRequest }) {
  if (request.severity === "pending") {
    return <p className="empty-note">Waiting for response…</p>;
  }

  const formattedBody = tryFormatBody(request.res_body);

  return (
    <div>
      <div className="status-display">
        {request.res_status !== null ? (
          <>
            <span className={`status-code ${statusBadgeClass(request.res_status).replace("badge-", "text-")}`}>
              {request.res_status}
            </span>
            <span className="status-text">{STATUS_TEXT[request.res_status] || ""}</span>
          </>
        ) : (
          <span className="status-code">—</span>
        )}
        {request.duration_ms !== null && (
          <span className={`duration-badge ${durationBadgeClass(request.duration_ms)}`}>
            {request.duration_ms}ms
          </span>
        )}
      </div>

      <div className="section">
        <div className="section-title">Response Headers</div>
        <KeyValueTable data={request.res_headers} />
      </div>

      <div className="section">
        <div className="section-title">Body</div>
        {formattedBody ? <JsonView text={formattedBody} /> : <p className="empty-note">Empty body</p>}
      </div>
    </div>
  );
}
