import { useState } from "react";
import { X } from "lucide-react";
import type { CapturedRequest } from "../types";
import { replayRequest } from "../api";
import { statusBadgeClass, tryFormatBody } from "../utils";

export default function ReplayModal({
  request,
  onClose,
  onReplayed,
}: {
  request: CapturedRequest;
  onClose: () => void;
  onReplayed: (r: CapturedRequest) => void;
}) {
  const [targetUrl, setTargetUrl] = useState(request.target_url);
  const [headersText, setHeadersText] = useState(JSON.stringify(request.req_headers || {}, null, 2));
  const [bodyText, setBodyText] = useState(tryFormatBody(request.req_body));
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState<CapturedRequest | null>(null);

  async function handleSend() {
    setError(null);
    let headers: Record<string, string> = {};
    let body: unknown = undefined;
    try {
      headers = headersText.trim() ? JSON.parse(headersText) : {};
    } catch {
      setError("Headers must be valid JSON");
      return;
    }
    if (bodyText.trim()) {
      try {
        body = JSON.parse(bodyText);
      } catch {
        body = bodyText;
      }
    }

    setSending(true);
    try {
      const record = await replayRequest(request.id, { target_url: targetUrl, headers, body });
      setResult(record);
      onReplayed(record);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Replay failed");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Replay request #{request.id}</h2>
          <button className="icon-btn" onClick={onClose}>
            <X size={16} />
          </button>
        </div>
        <div className="modal-body">
          <div>
            <div className="field-label">Target URL</div>
            <input
              className="modal-input"
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
            />
          </div>
          <div>
            <div className="field-label">Headers (JSON)</div>
            <textarea
              className="modal-textarea"
              value={headersText}
              onChange={(e) => setHeadersText(e.target.value)}
            />
          </div>
          <div>
            <div className="field-label">Body (JSON)</div>
            <textarea
              className="modal-textarea"
              value={bodyText}
              onChange={(e) => setBodyText(e.target.value)}
            />
          </div>
          {error && <p className="error-text">{error}</p>}

          {result && (
            <div className="replay-result">
              <div className="field-label">Result</div>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <span className={`badge ${statusBadgeClass(result.res_status)}`}>
                  {result.res_status ?? "—"}
                </span>
                <span>{result.summary}</span>
              </div>
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button className="btn" onClick={onClose}>
            Close
          </button>
          <button className="btn btn-primary" onClick={handleSend} disabled={sending}>
            {sending ? "Sending…" : "Send replay"}
          </button>
        </div>
      </div>
    </div>
  );
}
