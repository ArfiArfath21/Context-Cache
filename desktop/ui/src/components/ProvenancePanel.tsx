import type { ChunkResult } from "../types";

interface Props {
  result: ChunkResult;
  onClose: () => void;
}

export default function ProvenancePanel({ result, onClose }: Props) {
  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: "rgba(0,0,0,0.4)",
        display: "grid",
        placeItems: "center",
        zIndex: 99
      }}
    >
      <div className="panel" style={{ width: "min(600px, 90vw)" }}>
        <header style={{ display: "flex", justifyContent: "space-between" }}>
          <h3 style={{ margin: 0 }}>Provenance</h3>
          <button className="button" onClick={onClose}>
            Close
          </button>
        </header>
        <dl>
          <dt>Document</dt>
          <dd>{result.provenance?.document_id}</dd>
          <dt>Source</dt>
          <dd>{result.provenance?.uri || "Unknown"}</dd>
          <dt>Offsets</dt>
          <dd>
            {result.start_char} – {result.end_char}
          </dd>
          <dt>Deep Link</dt>
          <dd>
            {result.provenance?.deep_link ? (
              <a href={result.provenance.deep_link as string} target="_blank" rel="noreferrer">
                {result.provenance.deep_link as string}
              </a>
            ) : (
              "—"
            )}
          </dd>
        </dl>
      </div>
    </div>
  );
}
