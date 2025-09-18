import type { ChunkResult } from "../types";

interface Props {
  results: ChunkResult[];
  onInspect?: (result: ChunkResult) => void;
}

export default function ResultList({ results, onInspect }: Props) {
  if (!results.length) {
    return <p>No results yet. Try a different query.</p>;
  }
  return (
    <div className="result-list">
      {results.map((result, index) => (
        <article key={result.chunk_id} className="result-item">
          <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3>
              #{index + 1} – Score {result.score.toFixed(2)}
            </h3>
            <button className="button" onClick={() => onInspect?.(result)}>
              Provenance
            </button>
          </header>
          <pre>{result.text}</pre>
          {result.provenance?.deep_link && (
            <a href={result.provenance.deep_link as string} target="_blank" rel="noreferrer">
              Open source
            </a>
          )}
        </article>
      ))}
    </div>
  );
}
