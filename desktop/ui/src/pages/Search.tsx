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

  useEffect(() => {
    axiosClient<Source[]>("/sources").then(setSources).catch(() => undefined);
  }, []);

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
      setSelectedResult(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const openProvenance = (result: ChunkResult) => {
    setSelectedResult(result);
  };

  return (
    <div className="page-section" style={{ gap: "1.75rem" }}>
      <section className="panel" style={{ display: "grid", gap: "1.5rem" }}>
        <div>
          <h2 style={{ margin: 0 }}>Ask across your workspace</h2>
          <p className="panel-subtitle">Queries blend sparse and dense retrieval with reranking for precise results.</p>
        </div>
        <form onSubmit={runQuery} className="search-form">
          <input
            className="input"
            placeholder="Search for briefs, contracts, notes…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <Filters sources={sources} selectedSource={selectedSource} onChangeSource={setSelectedSource} />
          <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
            <button className="button" type="submit" disabled={loading}>
              {loading ? "Searching" : "Run search"}
            </button>
            {error && <span style={{ color: "tomato", fontSize: "0.9rem" }}>{error}</span>}
          </div>
        </form>
      </section>

      <section className="panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem" }}>
          <div>
            <h3 style={{ margin: 0 }}>Results</h3>
            <p className="panel-subtitle" style={{ marginTop: "0.4rem" }}>
              {results.length ? `${results.length} chunks ranked by relevance.` : "Run a search to populate this list."}
            </p>
          </div>
        </div>
        <ResultList results={results} onInspect={openProvenance} />
      </section>

      {selectedResult && <ProvenancePanel result={selectedResult} onClose={() => setSelectedResult(null)} />}
    </div>
  );
}
