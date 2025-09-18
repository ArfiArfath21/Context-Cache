import { useEffect, useRef, useState } from "react";

import { apiClient } from "../hooks/useApi";
import type { Source } from "../types";

interface HealthResponse {
  ok: boolean;
}

export default function StatusPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ingestNotice, setIngestNotice] = useState<string | null>(null);
  const noticeTimerRef = useRef<number | null>(null);

  const refresh = async () => {
    try {
      setLoading(true);
      setError(null);
      const [healthResp, sourcesResp] = await Promise.all([
        apiClient("/health"),
        apiClient("/sources")
      ]);
      setHealth(healthResp as HealthResponse);
      setSources(sourcesResp as Source[]);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh().catch(() => undefined);
    const listener = ((event: Event) => {
      const detail = (event as CustomEvent<{ message?: string }>).detail;
      if (detail?.message) {
        setIngestNotice(detail.message);
        if (noticeTimerRef.current) {
          window.clearTimeout(noticeTimerRef.current);
        }
        noticeTimerRef.current = window.setTimeout(() => {
          setIngestNotice(null);
          noticeTimerRef.current = null;
        }, 3200);
      }
    }) as EventListener;

    window.addEventListener("ctxc-ingest-update", listener);
    return () => {
      window.removeEventListener("ctxc-ingest-update", listener);
      if (noticeTimerRef.current) {
        window.clearTimeout(noticeTimerRef.current);
      }
    };
  }, []);

  return (
    <div className="page-section">
      <section className="panel">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "1rem" }}>
          <div>
            <h2 style={{ margin: 0 }}>Runtime status</h2>
            <p className="panel-subtitle">Live indicators from the API and your registered ingestion sources.</p>
          </div>
          <button className="button" onClick={refresh} disabled={loading}>
            {loading ? "Refreshing" : "Refresh"}
          </button>
        </div>
        {error && <p style={{ marginTop: "1rem", color: "tomato" }}>{error}</p>}
        {ingestNotice && (
          <p className="status-note" style={{ marginTop: "0.75rem" }}>
            {ingestNotice}
          </p>
        )}
        <div className="status-grid" style={{ marginTop: "1.5rem" }}>
          <div className="status-card">
            <h4>Backend health</h4>
            <p>{health?.ok ? "Backend reachable" : "Status unknown"}</p>
          </div>
          <div className="status-card">
            <h4>Registered sources</h4>
            <p>{sources.length}</p>
          </div>
        </div>
      </section>
      <section className="panel">
        <h3 style={{ marginTop: 0 }}>Sources</h3>
        <p className="panel-subtitle">
          The ingestion scheduler tracks these targets. Edit sources in Settings or trigger an on-demand ingest from the Settings tab.
        </p>
        <div className="sources-table-wrapper" style={{ marginTop: "1.25rem" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Label</th>
                <th>URI</th>
                <th>Kind</th>
              </tr>
            </thead>
            <tbody>
              {sources.length === 0 ? (
                <tr>
                  <td colSpan={3} style={{ padding: "1.2rem" }}>
                    No sources registered yet.
                  </td>
                </tr>
              ) : (
                sources.map((source) => (
                  <tr key={source.id}>
                    <td>{source.label || "—"}</td>
                    <td style={{ wordBreak: "break-word" }}>{source.uri}</td>
                    <td>{source.kind}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
