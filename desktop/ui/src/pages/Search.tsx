import { FormEvent, useEffect, useState } from "react";

import Filters from "../components/Filters";
import ProvenancePanel from "../components/ProvenancePanel";
import ResultList from "../components/ResultList";
import { axiosClient } from "../hooks/useApi";
import type { ChunkResult, QueryResponse, Source } from "../types";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ChunkResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [selectedSource, setSelectedSource] = useState<string | null>(null);
  const [selectedResult, setSelectedResult] = useState<ChunkResult | null>(null);

  const runQuery = async (event?: FormEvent) => {
    event?.preventDefault();
    if (!query.trim()) {
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const payload = await axiosClient<QueryResponse>("/query", "post", {
        query,
        k: 8,
        filters: selectedSource ? { source_ids: [selectedSource] } : undefined
      });
      setResults(payload.results);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    axiosClient<Source[]>("/sources").then(setSources).catch(() => {
      /* ignore */
    });
  }, []);

  return (
    <div className="panel">
      <form onSubmit={runQuery} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        <input
          className="input"
          placeholder="Search your context…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <Filters sources={sources} selectedSource={selectedSource} onChangeSource={setSelectedSource} />
        <div>
          <button className="button" type="submit" disabled={loading}>
            {loading ? "Searching…" : "Search"}
          </button>
        </div>
      </form>
      {error && <p style={{ color: "tomato" }}>{error}</p>}
      <section style={{ marginTop: "1.5rem" }}>
        <ResultList results={results} onInspect={setSelectedResult} />
      </section>
      {selectedResult && <ProvenancePanel result={selectedResult} onClose={() => setSelectedResult(null)} />}
    </div>
  );
}
