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
  const [message, setMessage] = useState<string | null>(null);

  const loadSources = async () => {
    const data = await axiosClient<Source[]>("/sources");
    setSources(data);
  };

  useEffect(() => {
    loadSources().catch(() => undefined);
  }, []);

  const saveHost = () => {
    localStorage.setItem("ctxc-host", host);
    setMessage("Host saved.");
    setTimeout(() => setMessage(null), 2000);
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

  const deleteSource = async (id: string) => {
    await axiosClient(`/sources/${id}`, "delete");
    loadSources();
  };

  return (
    <div className="panel" style={{ display: "grid", gap: "2rem" }}>
      <section>
        <h2>Backend Host</h2>
        <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
          <input className="input" value={host} onChange={(event) => setHost(event.target.value)} />
          <button className="button" onClick={saveHost}>
            Save
          </button>
        </div>
        {message && <p>{message}</p>}
      </section>
      <section>
        <h2>Register Source</h2>
        <form onSubmit={submitSource} style={{ display: "grid", gap: "0.75rem", maxWidth: "520px" }}>
          <input
            className="input"
            placeholder="URI or path"
            value={form.uri}
            onChange={(event) => setForm({ ...form, uri: event.target.value })}
            required
          />
          <input
            className="input"
            placeholder="Label"
            value={form.label}
            onChange={(event) => setForm({ ...form, label: event.target.value })}
          />
          <input
            className="input"
            placeholder="Include glob"
            value={form.include_glob}
            onChange={(event) => setForm({ ...form, include_glob: event.target.value })}
          />
          <input
            className="input"
            placeholder="Exclude glob"
            value={form.exclude_glob}
            onChange={(event) => setForm({ ...form, exclude_glob: event.target.value })}
          />
          <button className="button" type="submit">
            Add Source
          </button>
        </form>
      </section>
      <section>
        <h2>Existing Sources</h2>
        <table className="table">
          <thead>
            <tr>
              <th>Label</th>
              <th>URI</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {sources.map((source) => (
              <tr key={source.id}>
                <td>{source.label || "—"}</td>
                <td>{source.uri}</td>
                <td>
                  <button className="button" onClick={() => deleteSource(source.id)}>
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
