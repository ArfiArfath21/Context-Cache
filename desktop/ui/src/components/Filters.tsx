import type { Source } from "../types";

interface Props {
  sources: Source[];
  selectedSource: string | null;
  onChangeSource: (sourceId: string | null) => void;
}

export default function Filters({ sources, selectedSource, onChangeSource }: Props) {
  return (
    <div className="filters">
      <label>
        Source
        <select
          className="input"
          value={selectedSource || ""}
          onChange={(event) => {
            const value = event.target.value || null;
            onChangeSource(value);
          }}
        >
          <option value="">All sources</option>
          {sources.map((source) => (
            <option key={source.id} value={source.id}>
              {source.label || source.uri}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
