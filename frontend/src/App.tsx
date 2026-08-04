import { useCallback, useEffect, useMemo, useState } from "react";
import { CircleDot, Trash2 } from "lucide-react";
import type { CapturedRequest, StatusFilter } from "./types";
import { clearRequests, connectWebSocket, fetchRequests } from "./api";
import RequestFeed from "./components/RequestFeed";
import DetailPanel from "./components/DetailPanel";
import ReplayModal from "./components/ReplayModal";
import SendRequestPanel from "./components/SendRequestPanel";

export default function App() {
  const [requests, setRequests] = useState<CapturedRequest[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [connected, setConnected] = useState(false);
  const [replayTarget, setReplayTarget] = useState<CapturedRequest | null>(null);
  const [loading, setLoading] = useState(true);

  const loadRequests = useCallback((status: StatusFilter) => {
    fetchRequests(50, status)
      .then(setRequests)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadRequests(filter);
  }, [filter, loadRequests]);

  useEffect(() => {
    const disconnect = connectWebSocket(
      (msg) => {
        if (msg.type === "request_completed") {
          setRequests((prev) => {
            const record = msg.data;
            if (filter !== "all" && record.severity !== filter) {
              return prev.filter((r) => r.id !== record.id);
            }
            const exists = prev.some((r) => r.id === record.id);
            const next = exists ? prev.map((r) => (r.id === record.id ? record : r)) : [record, ...prev];
            return next.slice(0, 50);
          });
        }
      },
      setConnected
    );
    return () => {
      disconnect();
    };
  }, [filter]);

  const selected = useMemo(() => requests.find((r) => r.id === selectedId) || null, [requests, selectedId]);

  function handleNewRequest(record: CapturedRequest) {
    setRequests((prev) => {
      const exists = prev.some((r) => r.id === record.id);
      const next = exists ? prev.map((r) => (r.id === record.id ? record : r)) : [record, ...prev];
      return next.slice(0, 50);
    });
    setSelectedId(record.id);
  }

  async function handleClear() {
    await clearRequests();
    setRequests([]);
    setSelectedId(null);
  }

  const stats = useMemo(() => {
    const total = requests.length;
    const finished = requests.filter((r) => r.severity !== "pending");
    const successes = finished.filter((r) => r.severity === "success").length;
    const errors = finished.filter((r) => r.severity === "error").length;
    const durations = finished.map((r) => r.duration_ms).filter((d): d is number => d !== null);
    const avg = durations.length ? Math.round(durations.reduce((a, b) => a + b, 0) / durations.length) : 0;
    const successRate = finished.length ? Math.round((successes / finished.length) * 100) : 0;
    return { total, successRate, errors, avg };
  }, [requests]);

  return (
    <div className="app">
      <header className="app-header">
        <CircleDot size={16} className="logo-dot" />
        <h1>API Request Inspector</h1>
        <div className="header-spacer" />
        <span className={`live-badge ${connected ? "" : "offline"}`}>
          <span className="live-dot" />
          {connected ? "LIVE" : "OFFLINE"}
        </span>
        <button className="btn btn-danger" onClick={handleClear}>
          <Trash2 size={13} /> Clear
        </button>
      </header>

      <div className="stats-bar">
        <div className="stat-cell">
          <div className="stat-label">Requests</div>
          <div className="stat-value">{stats.total}</div>
        </div>
        <div className="stat-cell">
          <div className="stat-label">Success %</div>
          <div className="stat-value">{stats.successRate}%</div>
        </div>
        <div className="stat-cell">
          <div className="stat-label">Errors</div>
          <div className="stat-value">{stats.errors}</div>
        </div>
        <div className="stat-cell">
          <div className="stat-label">Avg response time</div>
          <div className="stat-value">{stats.avg}ms</div>
        </div>
      </div>

      <SendRequestPanel onSent={handleNewRequest} />

      <div className="main-layout">
        <RequestFeed
          requests={requests}
          selectedId={selectedId}
          onSelect={(r) => setSelectedId(r.id)}
          filter={filter}
          onFilterChange={setFilter}
        />
        <DetailPanel request={loading ? null : selected} onReplay={setReplayTarget} />
      </div>

      {replayTarget && (
        <ReplayModal
          request={replayTarget}
          onClose={() => setReplayTarget(null)}
          onReplayed={(record) => {
            handleNewRequest(record);
          }}
        />
      )}
    </div>
  );
}
