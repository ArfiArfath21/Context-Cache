import { FormEvent, useEffect, useState } from "react";

import { axiosClient } from "../hooks/useApi";
import type { Source } from "../types";

interface SourceFormState {
  uri: string;
  label: string;
  include_glob: string;
  exclude_glob: string;
}

const INITIAL_FORM: SourceFormState = {
  uri: "",
  label: "",
  include_glob: "",
  exclude_glob: ""
};

export default function SettingsPage() {
  const [host, setHost] = useState(() => localStorage.getItem("ctxc-host") || "http://127.0.0.1:5173");
  const [sources, setSources] = useState<Source[]>([]);
  const [form, setForm] = useState<SourceFormState>(INITIAL_FORM);
  const [hostMessage, setHostMessage] = useState<string | null>(null);
  const [ingestMessage, setIngestMessage] = useState<string | null>(null);
  const [ingestBusy, setIngestBusy] = useState(false);

  const loadSources = async () => {
    const data = await axiosClient<Source[]>("/sources");
    setSources(data);
  };

  useEffect(() => {
    loadSources().catch(() => undefined);
  }, []);

  const saveHost = () => {
    const trimmed = host.trim();
    localStorage.setItem("ctxc-host", trimmed);
    window.dispatchEvent(new Event("ctxc-host-changed"));
    setHostMessage(`Backend host saved (${trimmed}).`);
    window.setTimeout(() => setHostMessage(null), 2400);
  };

  const submitSource = async (event: FormEvent) => {
    event.preventDefault();
    await axiosClient<Source>("/sources", "post", {
      uri: form.uri,
      label: form.label || undefined,
      include_glob: form.include_glob || undefined,
      exclude_glob: form.exclude_glob || undefined
    });
    setForm(INITIAL_FORM);
    loadSources();
  };

  const triggerIngest = async (payload: Record<string, unknown>) => {
    setIngestBusy(true);
    try {
      await axiosClient("/ingest", "post", payload);
      const castPayload = payload as { sources?: string[] };
      const detail = castPayload.sources && castPayload.sources.length > 0
        ? `Source ${castPayload.sources[0]}`
        : "All sources";
      const note = `${detail} queued for ingestion. Monitor progress on the Status tab.`;
      setIngestMessage(note);
      window.dispatchEvent(new CustomEvent("ctxc-ingest-update", { detail: { message: note } }));
      window.setTimeout(() => setIngestMessage(null), 3200);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setIngestMessage(`Ingest request failed: ${message}`);
      window.setTimeout(() => setIngestMessage(null), 3600);
    } finally {
      setIngestBusy(false);
    }
  };

  const deleteSource = async (id: string) => {
    await axiosClient(`/sources/${id}`, "delete");
    loadSources();
  };

  return (
    <div className="page-section">
      <section className="panel" style={{ display: "grid", gap: "1.6rem" }}>
        <div>
          <h2 style={{ margin: 0 }}>Connectivity</h2>
          <p className="panel-subtitle">Point the desktop client at any reachable Context Cache backend.</p>
        </div>
        <div className="host-row">
          <input className="input" value={host} onChange={(event) => setHost(event.target.value)} />
          <button className="button" type="button" onClick={saveHost}>
            Save host
          </button>
          {hostMessage && <span className="status-note">{hostMessage}</span>}
        </div>
        <div className="host-row">
          <button className="button-outline" type="button" onClick={() => triggerIngest({ all: true })} disabled={ingestBusy}>
            {ingestBusy ? "Ingesting…" : "Ingest all sources"}
          </button>
          {ingestMessage && <span className="status-note">{ingestMessage}</span>}
        </div>
      </section>

      <div className="settings-grid">
        <section className="panel settings-form">
          <div>
            <h2 style={{ margin: 0 }}>Register a source</h2>
            <p className="panel-subtitle">
              Add a folder, file, or remote URI. Optional glob filters let you choose what is indexed.
            </p>
          </div>
          <form onSubmit={submitSource} className="settings-form">
            <label className="field">
              <span>Location</span>
              <input
                className="input"
                placeholder="~/Documents/Notes"
                value={form.uri}
                onChange={(event) => setForm({ ...form, uri: event.target.value })}
                required
              />
            </label>
            <label className="field">
              <span>Label (optional)</span>
              <input
                className="input"
                placeholder="Team knowledge"
                value={form.label}
                onChange={(event) => setForm({ ...form, label: event.target.value })}
              />
            </label>
            <label className="field">
              <span>Include glob</span>
              <input
                className="input"
                placeholder="**/*.md"
                value={form.include_glob}
                onChange={(event) => setForm({ ...form, include_glob: event.target.value })}
              />
            </label>
            <label className="field">
              <span>Exclude glob</span>
              <input
                className="input"
                placeholder="**/archive/**"
                value={form.exclude_glob}
                onChange={(event) => setForm({ ...form, exclude_glob: event.target.value })}
              />
            </label>
            <div>
              <button className="button" type="submit">
                Add source
              </button>
            </div>
          </form>
        </section>

        <section className="panel" style={{ overflow: "hidden" }}>
          <h2 style={{ margin: "0 0 0.6rem 0" }}>Existing sources</h2>
          <p className="panel-subtitle" style={{ marginBottom: "1rem" }}>
            Trigger ingestion on demand or remove an entry if you no longer need it tracked.
          </p>
          <div className="sources-table-wrapper">
            <table className="table">
              <thead>
                <tr>
                  <th>Label</th>
                  <th>URI</th>
                  <th style={{ width: "180px" }}>Actions</th>
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
                      <td>
                        <div className="source-actions">
                          <button
                            className="button-outline"
                            type="button"
                            onClick={() => triggerIngest({ sources: [source.id] })}
                            disabled={ingestBusy}
                          >
                            Ingest
                          </button>
                          <button className="button-outline" type="button" onClick={() => deleteSource(source.id)}>
                            Remove
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
