import type { ChunkResult } from "../types";
import { openExternalLink } from "../utils/external";

interface Props {
  results: ChunkResult[];
  onInspect?: (result: ChunkResult) => void;
}

export default function ResultList({ results, onInspect }: Props) {
  if (!results.length) {
    return <p className="status-note">No results yet. Run a query to populate this view.</p>;
  }

  return (
    <div className="result-list">
      {results.map((result, index) => (
        <article key={result.chunk_id} className="result-item">
          <header style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem" }}>
            <div>
              <h3>{index + 1}. Score {result.score.toFixed(2)}</h3>
              <p className="status-note" style={{ margin: "0.35rem 0 0" }}>
                Chunk ID {result.chunk_id}
              </p>
            </div>
            <button className="button-outline" type="button" onClick={() => onInspect?.(result)}>
              Inspect chunk
            </button>
          </header>
          <pre>{result.text}</pre>
          <footer style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem" }}>
            <span className="status-note">Document {result.provenance?.document_id ?? "—"}</span>
            {typeof result.provenance?.deep_link === "string" && result.provenance.deep_link.trim() ? (
              <button
                className="button-outline"
                type="button"
                onClick={() => void openExternalLink(result.provenance!.deep_link as string)}
              >
                Open source
              </button>
            ) : (
              <span className="status-note">No deep link available</span>
            )}
          </footer>
        </article>
      ))}
    </div>
  );
}
