import type { CapturedRequest, ProxyPayload, ReplayPayload, StatusFilter, WsMessage } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
const WS_BASE = API_BASE.replace(/^http/, "ws");

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

export function sendProxyRequest(payload: ProxyPayload): Promise<CapturedRequest> {
  return fetch(`${API_BASE}/proxy`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).then((res) => handle<CapturedRequest>(res));
}

export function fetchRequests(limit = 50, status: StatusFilter = "all"): Promise<CapturedRequest[]> {
  return fetch(`${API_BASE}/requests?limit=${limit}&status=${status}`).then((res) =>
    handle<CapturedRequest[]>(res)
  );
}

export function replayRequest(id: number, payload: ReplayPayload): Promise<CapturedRequest> {
  return fetch(`${API_BASE}/requests/${id}/replay`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).then((res) => handle<CapturedRequest>(res));
}

export function clearRequests(): Promise<void> {
  return fetch(`${API_BASE}/requests`, { method: "DELETE" }).then((res) => handle(res));
}

export function connectWebSocket(
  onMessage: (msg: WsMessage) => void,
  onStatusChange?: (connected: boolean) => void
): () => void {
  let ws: WebSocket | null = null;
  let closedByCaller = false;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;

  const connect = () => {
    ws = new WebSocket(`${WS_BASE}/ws`);
    ws.onopen = () => onStatusChange?.(true);
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as WsMessage;
        onMessage(msg);
      } catch {
        // ignore malformed messages
      }
    };
    ws.onclose = () => {
      onStatusChange?.(false);
      if (!closedByCaller) {
        retryTimer = setTimeout(connect, 2000);
      }
    };
  };

  connect();

  return () => {
    closedByCaller = true;
    if (retryTimer) clearTimeout(retryTimer);
    ws?.close();
  };
}
