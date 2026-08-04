import { AlertTriangle, CheckCircle2, Lightbulb, Repeat } from "lucide-react";
import type { CapturedRequest } from "../types";

export default function AnalysisTab({
  request,
  onReplay,
}: {
  request: CapturedRequest;
  onReplay: () => void;
}) {
  if (request.severity === "pending") {
    return <p className="empty-note">Analysis will appear once the response arrives.</p>;
  }

  const issues = request.detected_issues || [];
  const checkedFields = ["Authorization", "Content-Type", "URL", "Body"];
  const issueByField = new Map(issues.map((i) => [i.field, i]));

  return (
    <div>
      {request.error_code && (
        <div className="section">
          <span className={`badge ${request.severity === "success" ? "badge-2xx" : request.severity === "warning" ? "badge-5xx" : "badge-4xx"}`}>
            {request.error_code}
          </span>
        </div>
      )}

      <div className="section">
        <div className="section-title">Detected Checks</div>
        <div className="issue-pills">
          {checkedFields.map((field) => {
            const issue = issueByField.get(field);
            return (
              <span key={field} className={`issue-pill ${issue ? "bad" : "ok"}`}>
                {issue ? <AlertTriangle size={13} /> : <CheckCircle2 size={13} />}
                {field}
              </span>
            );
          })}
          {issues
            .filter((i) => !checkedFields.includes(i.field))
            .map((i, idx) => (
              <span key={`extra-${idx}`} className="issue-pill bad">
                <AlertTriangle size={13} />
                {i.field}
              </span>
            ))}
        </div>
        {issues.length > 0 && (
          <div style={{ marginTop: 12 }}>
            {issues.map((issue, idx) => (
              <div className="detected-issue-row" key={idx}>
                <span className="detected-issue-field">{issue.field}</span>
                <span>{issue.issue}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {request.severity === "error" && request.explanation && (
        <div className="section">
          <div className="info-box error">
            <div className="info-box-title">
              <AlertTriangle size={13} /> Why it failed
            </div>
            {request.explanation}
          </div>
        </div>
      )}

      {request.suggestion && (
        <div className="section">
          <div className="info-box suggestion">
            <div className="info-box-title">
              <Lightbulb size={13} /> Suggested fix
            </div>
            {request.suggestion}
          </div>
        </div>
      )}

      <button className="btn btn-primary" onClick={onReplay}>
        <Repeat size={14} /> Replay request
      </button>
    </div>
  );
}
