PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA encoding = 'UTF-8';

-- Sources registered with the watcher/ingest pipeline
CREATE TABLE IF NOT EXISTS sources (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  uri TEXT NOT NULL,
  label TEXT,
  include_glob TEXT,
  exclude_glob TEXT,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sources_uri ON sources(uri);

-- Documents extracted from sources
CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  external_id TEXT,
  title TEXT,
  author TEXT,
  created_ts INTEGER,
  modified_ts INTEGER,
  mime TEXT,
  sha256 TEXT UNIQUE NOT NULL,
  raw_bytes BLOB,
  text TEXT,
  meta_json TEXT,
  size_bytes INTEGER,
  is_deleted INTEGER DEFAULT 0,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source_id);
CREATE INDEX IF NOT EXISTS idx_documents_sha ON documents(sha256);
CREATE INDEX IF NOT EXISTS idx_documents_deleted ON documents(is_deleted);

-- Full text search virtual table for document-level queries
CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
  text,
  content='documents',
  content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
  INSERT INTO documents_fts(rowid, text) VALUES (new.rowid, new.text);
END;

CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
  DELETE FROM documents_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
  UPDATE documents_fts SET text = new.text WHERE rowid = new.rowid;
END;

-- Chunk table storing retrieval units
CREATE TABLE IF NOT EXISTS chunks (
  id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  ordinal INTEGER NOT NULL,
  start_char INTEGER NOT NULL,
  end_char INTEGER NOT NULL,
  text TEXT NOT NULL,
  token_count INTEGER NOT NULL,
  meta_json TEXT,
  created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_ordinal ON chunks(document_id, ordinal);

-- Embeddings table allows multiple embedding models per chunk
CREATE TABLE IF NOT EXISTS embeddings (
  chunk_id TEXT NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
  model TEXT NOT NULL,
  dim INTEGER NOT NULL,
  vector BLOB NOT NULL,
  style TEXT DEFAULT 'dense',
  created_at INTEGER NOT NULL,
  PRIMARY KEY (chunk_id, model)
);

-- Ingest job tracking
CREATE TABLE IF NOT EXISTS ingest_jobs (
  id TEXT PRIMARY KEY,
  source_id TEXT,
  started_at INTEGER NOT NULL,
  finished_at INTEGER,
  status TEXT NOT NULL,
  stats_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_ingest_jobs_source ON ingest_jobs(source_id);

CREATE TABLE IF NOT EXISTS ingest_events (
  id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL REFERENCES ingest_jobs(id) ON DELETE CASCADE,
  stage TEXT NOT NULL,
  message TEXT,
  level TEXT DEFAULT 'info',
  created_at INTEGER NOT NULL
);

-- Query history for analytics and `/why`
CREATE TABLE IF NOT EXISTS queries (
  id TEXT PRIMARY KEY,
  query TEXT NOT NULL,
  filters_json TEXT,
  rerank_enabled INTEGER DEFAULT 0,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS query_results (
  id TEXT PRIMARY KEY,
  query_id TEXT NOT NULL REFERENCES queries(id) ON DELETE CASCADE,
  chunk_id TEXT NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
  rank INTEGER NOT NULL,
  score REAL NOT NULL,
  provenance_json TEXT,
  created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_query_results_query ON query_results(query_id);

-- Tags for documents/chunks
CREATE TABLE IF NOT EXISTS tags (
  id TEXT PRIMARY KEY,
  label TEXT NOT NULL UNIQUE,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS document_tags (
  document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  tag_id TEXT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  PRIMARY KEY (document_id, tag_id)
);

CREATE TABLE IF NOT EXISTS chunk_tags (
  chunk_id TEXT NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
  tag_id TEXT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  PRIMARY KEY (chunk_id, tag_id)
);

-- Key-value settings (for feature flags / sync state)
CREATE TABLE IF NOT EXISTS kv_store (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at INTEGER NOT NULL
);
