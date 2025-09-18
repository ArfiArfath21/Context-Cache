import { useEffect } from "react";

import type { ChunkResult } from "../types";
import { openExternalLink } from "../utils/external";

interface Props {
  result: ChunkResult;
  onClose: () => void;
}

export default function ProvenancePanel({ result, onClose }: Props) {
  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  const provenance = result.provenance;

  return (
    <div className="drawer" role="dialog" aria-modal="true" onClick={onClose}>
      <aside className="drawer-panel" onClick={(event) => event.stopPropagation()}>
        <header className="drawer-header">
          <div>
            <h3>Chunk details</h3>
            <p className="panel-subtitle">
              Chunk {result.chunk_id} · Score {result.score.toFixed(2)}
            </p>
          </div>
          <button className="button-outline" type="button" onClick={onClose}>
            Close
          </button>
        </header>

        <section className="drawer-section">
          <h4>Excerpt</h4>
          <pre className="excerpt">{result.text}</pre>
        </section>

        <section className="drawer-section">
          <h4>Metadata</h4>
          <dl className="meta-grid">
            <div>
              <dt>Document ID</dt>
              <dd>{provenance?.document_id ?? "—"}</dd>
            </div>
            <div>
              <dt>Source URI</dt>
              <dd style={{ wordBreak: "break-word" }}>{provenance?.uri ?? "Unknown"}</dd>
            </div>
            <div>
              <dt>Offsets</dt>
              <dd>
                {result.start_char} – {result.end_char}
              </dd>
            </div>
            <div>
              <dt>Deep link</dt>
              <dd>
                {typeof provenance?.deep_link === "string" && provenance.deep_link.trim() ? (
                  <button
                    className="button-outline"
                    type="button"
                    onClick={() => void openExternalLink(provenance.deep_link as string)}
                  >
                    Open source
                  </button>
                ) : (
                  <span className="status-note">No deep link available</span>
                )}
              </dd>
            </div>
          </dl>
        </section>
      </aside>
    </div>
  );
}
