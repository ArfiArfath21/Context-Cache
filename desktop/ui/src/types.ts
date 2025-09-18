export interface ChunkResult {
  chunk_id: string;
  document_id: string;
  score: number;
  text: string;
  start_char: number;
  end_char: number;
  provenance: Record<string, unknown> & {
    uri?: string;
    deep_link?: string;
  };
}

export interface QueryResponse {
  query_id: string;
  results: ChunkResult[];
}

export interface Source {
  id: string;
  label?: string | null;
  kind: string;
  uri: string;
  include_glob?: string | null;
  exclude_glob?: string | null;
  created_at: string;
  updated_at: string;
}

export interface IngestStats {
  processed: number;
  skipped: number;
  failed: number;
  chunks: number;
}

export interface IngestResponse {
  job_id: string;
  stats: IngestStats;
}
