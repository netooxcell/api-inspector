import { useState } from "react";
import { Plus, Send, Trash2 } from "lucide-react";
import { sendProxyRequest } from "../api";
import type { CapturedRequest } from "../types";

const METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"];

interface HeaderRow {
  key: string;
  value: string;
}

export default function SendRequestPanel({ onSent }: { onSent: (r: CapturedRequest) => void }) {
  const [method, setMethod] = useState("GET");
  const [url, setUrl] = useState("");
  const [headerRows, setHeaderRows] = useState<HeaderRow[]>([{ key: "", value: "" }]);
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function updateRow(idx: number, field: "key" | "value", value: string) {
    setHeaderRows((rows) => rows.map((r, i) => (i === idx ? { ...r, [field]: value } : r)));
  }

  function addRow() {
    setHeaderRows((rows) => [...rows, { key: "", value: "" }]);
  }

  function removeRow(idx: number) {
    setHeaderRows((rows) => rows.filter((_, i) => i !== idx));
  }

  async function handleSend() {
    setError(null);
    if (!url.trim()) {
      setError("Target URL is required");
      return;
    }

    const headers: Record<string, string> = {};
    for (const row of headerRows) {
      if (row.key.trim()) headers[row.key.trim()] = row.value;
    }

    let parsedBody: unknown = undefined;
    if (body.trim()) {
      try {
        parsedBody = JSON.parse(body);
      } catch {
        parsedBody = body;
      }
    }

    setSending(true);
    try {
      const record = await sendProxyRequest({
        target_url: url.trim(),
        method,
        headers,
        body: parsedBody,
      });
      onSent(record);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="send-panel">
      <div className="send-panel-inner">
        <div className="send-row">
          <select value={method} onChange={(e) => setMethod(e.target.value)}>
            {METHODS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
          <input
            type="text"
            placeholder="https://api.example.com/v1/resource"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        </div>

        <div>
          <div className="field-label">Headers</div>
          {headerRows.map((row, idx) => (
            <div className="header-row" key={idx} style={{ marginBottom: 6 }}>
              <input
                placeholder="Header name"
                value={row.key}
                onChange={(e) => updateRow(idx, "key", e.target.value)}
              />
              <input
                placeholder="Value"
                value={row.value}
                onChange={(e) => updateRow(idx, "value", e.target.value)}
              />
              <button className="icon-btn" onClick={() => removeRow(idx)} aria-label="Remove header">
                <Trash2 size={13} />
              </button>
            </div>
          ))}
          <button className="btn" onClick={addRow}>
            <Plus size={13} /> Add header
          </button>
        </div>

        <div>
          <div className="field-label">Body</div>
          <textarea
            className="body-input"
            placeholder='{"key": "value"}'
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
        </div>

        {error && <p className="error-text">{error}</p>}

        <div className="send-panel-footer">
          <span />
          <button className="btn btn-primary" onClick={handleSend} disabled={sending}>
            <Send size={14} /> {sending ? "Sending…" : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}
