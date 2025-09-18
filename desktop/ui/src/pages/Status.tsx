import { useEffect, useState } from "react";

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

  const refresh = async () => {
    try {
      setLoading(true);
      setError(null);
      const [healthResp, sourcesResp] = await Promise.all([
        apiClient("/health"),
        apiClient("/sources")
      ]);
      setHealth(healthResp);
      setSources(sourcesResp as Source[]);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  return (
    <div className="panel">
      <header style={{ display: "flex", alignItems: "center", marginBottom: "1rem" }}>
        <h2 style={{ margin: 0, flex: 1 }}>System Status</h2>
        <button className="button" onClick={refresh} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </header>
      {error && <p style={{ color: "tomato" }}>{error}</p>}
      <div className="status-grid">
        <div className="status-card">
          <h4>Health</h4>
          <p>{health?.ok ? "✅ Backend reachable" : "⚠️ Unknown"}</p>
        </div>
        <div className="status-card">
          <h4>Registered Sources</h4>
          <p>{sources.length}</p>
        </div>
      </div>
      <section style={{ marginTop: "2rem" }}>
        <h3>Sources</h3>
        <table className="table">
          <thead>
            <tr>
              <th>Label</th>
              <th>URI</th>
              <th>Kind</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((source) => (
              <tr key={source.id}>
                <td>{source.label || "—"}</td>
                <td>{source.uri}</td>
                <td>{source.kind}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
