# Context Cache — full spec (v0.1)

## One-liner

A **local knowledge layer** that watches your files/mail/notes, builds a **private vector + metadata index**, and exposes a **RAG API** any LLM can call. Answers always come with **provenance** (“why this answer?”).

## Core promises

1. **Private by default**: everything runs locally; optional encrypted sync.
2. **Explainable**: every answer shows exact source chunks and scores.
3. **Fast**: sub-200ms top-k retrieval on 100k+ chunks on a laptop.
4. **Simple to integrate**: `http://localhost:5173/query` returns JSON your model can consume.

---

# System overview

## Components

* **Watcher**: monitors sources (folders, mailbox exports, notes) → emits “documents”.
* **Ingestor**: normalizes docs (text extraction, chunking, embeddings) → “chunks”.
* **Index**: vector store + metadata store.
* **RAG API**: local HTTP server exposing `/ingest`, `/query`, `/rerank`, `/why`.
* **UI (Desktop)**: minimal Tauri/Electron app for status, search, and provenance.
* **CLI**: mirrors API for headless use (`ctxc ingest`, `ctxc query`).

## Suggested stack

* **Runtime:** Python 3.11 for backend; **Tauri** (Rust + Web) for desktop (fast, small).
* **Vector store:**

  * MVP: **SQLite** + **sqlite-vss** (or **FAISS** if you prefer a pure Python path).
  * Alt: **Qdrant** (embedded) if you want HNSW out of the box.
* **Metadata store:** SQLite (FTS5 enabled for hybrid search).
* **Embeddings:** `intfloat/e5-small-v2` (fast & strong) via `sentence-transformers`.
* **Reranker (optional):** `cross-encoder/ms-marco-MiniLM-L-6-v2`.
* **Chunking:** semantic paragraph splitter + token budget (see algorithm below).
* **Extractors:** `textract`/`pymupdf` for PDFs, `python-docx`, `odfpy`, `markdown-it`.
* **OS file watch:** `watchdog`.
* **Security:** OS keychain for secrets, libsodium/XChaCha20-Poly1305 for optional sync.

---

# Data model

## Entities

```text
Source             – logical origin (folder path, mailbox export, note repo)
Document           – a file/email/note with its raw text & fields
Chunk              – digestible unit for retrieval (text + span offsets)
Embedding          – vector for a chunk (model, dim, hash)
IngestJob          – pipeline run with status + stats
Query              – a retrieval request (query text + filters)
Result             – a ranked chunk hit with scores + provenance
```

## SQLite schema (DDL)

```sql
-- Sources
CREATE TABLE sources (
  id TEXT PRIMARY KEY,                 -- uuid
  kind TEXT NOT NULL,                  -- 'folder' | 'mbox' | 'markdown' | 'notion_export' | ...
  uri TEXT NOT NULL,                   -- e.g. file:///Users/arfi/Notes
  label TEXT,                          -- human-friendly
  include_glob TEXT,                   -- e.g. **/*.{pdf,md,txt}
  exclude_glob TEXT,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

-- Documents
CREATE TABLE documents (
  id TEXT PRIMARY KEY,                 -- uuid
  source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  external_id TEXT,                    -- e.g. file path or email id
  title TEXT,
  author TEXT,
  created_ts INTEGER,                  -- unix ms, if known
  modified_ts INTEGER,                 -- unix ms
  mime TEXT,                           -- 'application/pdf', 'text/markdown'
  sha256 TEXT UNIQUE NOT NULL,         -- raw bytes hash
  raw_bytes BLOB,                      -- optional: store; can be NULL if file on disk
  text TEXT,                           -- normalized extracted text
  meta_json TEXT,                      -- {tags:[],url:"",project:"",...}
  size_bytes INTEGER,
  is_deleted INTEGER DEFAULT 0,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

-- Full-text index for doc-level search
CREATE VIRTUAL TABLE documents_fts USING fts5(
  text, content='documents', content_rowid='rowid'
);

-- Chunks
CREATE TABLE chunks (
  id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  ordinal INTEGER NOT NULL,            -- 0..N
  start_char INTEGER NOT NULL,
  end_char INTEGER NOT NULL,
  text TEXT NOT NULL,
  token_count INTEGER NOT NULL,
  meta_json TEXT,                      -- section headers, page numbers, etc.
  created_at INTEGER NOT NULL
);

-- Embeddings (separate for multi-model support)
CREATE TABLE embeddings (
  chunk_id TEXT NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
  model TEXT NOT NULL,                 -- 'e5-small-v2'
  dim INTEGER NOT NULL,
  vector BLOB NOT NULL,                -- packed float32[]
  style TEXT DEFAULT 'dense',          -- 'dense'|'sparse'|'hybrid'
  created_at INTEGER NOT NULL,
  PRIMARY KEY (chunk_id, model)
);

-- sqlite-vss (or FAISS) index (example for sqlite-vss)
CREATE VIRTUAL TABLE vss_e5_small USING vss0(
  chunk_id TEXT,                       -- mirror of chunks.id
  vector(384)                          -- set dim per model
);

-- Ingest jobs
CREATE TABLE ingest_jobs (
  id TEXT PRIMARY KEY,
  source_id TEXT,
  status TEXT NOT NULL,                -- 'queued'|'running'|'done'|'error'
  started_at INTEGER,
  finished_at INTEGER,
  stats_json TEXT                      -- timings, counts, errors
);

-- Queries history (optional)
CREATE TABLE queries (
  id TEXT PRIMARY KEY,
  text TEXT NOT NULL,
  filters_json TEXT,
  created_at INTEGER NOT NULL,
  results_json TEXT                    -- cached top-k ids + scores (for /why later)
);
```

> If using FAISS, store vectors in a sidecar index + `embeddings` table keeps truth.

---

# Ingestion pipeline

## Watcher → Ingestor flow

1. **Detect change** (create/modify/delete)
2. **Document loader**:

   * PDFs: extract per page with `pymupdf`, store page map in `meta_json.pages[]`.
   * Emails (mbox/EML): parse headers, HTML→text, attachments optional.
   * MD/TXT/DOCX: normalize newlines, strip boilerplate.
3. **Normalization**: lower noise, canon quotes, language detect (`langid`) → `lang` meta.
4. **Chunking algorithm** (semantic paragraphs + token budget):

   * Split by headings & blank lines; then greedily merge until `~512 tokens` (target) with soft cap `768`.
   * Respect page/section boundaries; store `section_title`, `page_from..to`.
   * Compute `token_count` via `tiktoken` (or fast approx).
5. **Embeddings**: encode with e5-small-v2: `embed("query: ...") / embed("passage: ...")` convention.
6. **Index write**:

   * Upsert `documents`, `chunks`, `embeddings`.
   * Insert vectors to VSS/FAISS; keep `sha256` to avoid re-ingest.
7. **FTS**: insert `text` into `documents_fts`.
8. **Stats** recorded in `ingest_jobs`.

## Deduplication

* **File-level**: `sha256(raw_bytes)`. If path changes but hash same → update `external_id` only.
* **Chunk-level near-dup** (optional): MinHash or SimHash on normalized text to prune boilerplate.

## Deletions / tombstones

* If file deleted, mark `documents.is_deleted=1`; keep chunks but down-weight during retrieval; background GC actually removes after 30 days (configurable).

---

# Retrieval & ranking

## Hybrid retrieval

1. **Dense**: ANN top-K (e.g., 100) from `vss_e5_small`.
2. **Sparse**: BM25/FTS top-J (e.g., 100) over `documents_fts`.
3. **Merge**: normalize scores, reciprocal rank fusion (RRF).
4. **Rerank (optional but recommended)**: cross-encoder rerank top-M (e.g., 50) → final top-k (e.g., 8).
5. **Diversify**: maximal marginal relevance (MMR) to reduce same-doc repeats (λ=0.5).
6. **Provenance**: include doc title, path/URL, page numbers, section titles, timestamps, and a **reproducible permalink** (local deep link `ctxc://doc/<id>?chunk=<chunkId>`).

## Filters

* By **source** (`source_id` or label), **mime**, **time** (`modified_ts` ranges), **tags** (from `meta_json.tags[]`), **project**.

---

# Local HTTP API (RAG)

Base URL: `http://127.0.0.1:5173`

All requests/response bodies are JSON. Errors use Problem Details (RFC 7807).

## `POST /ingest`

Trigger an ingest job for one or more sources, or direct file paths.

```json
{
  "sources": ["3c5a-...-9a1e"],       // optional
  "paths": ["/Users/arfi/Notes", "/Users/arfi/Downloads/meeting.pdf"],
  "include_glob": "**/*.{md,txt,pdf}",
  "exclude_glob": "**/.git/**",
  "priority": "normal"                 // 'low'|'normal'|'high'
}
```

**Response**

```json
{"job_id":"b2a1-...","status":"queued"}
```

## `GET /ingest/:job_id`

Returns status and stats.

```json
{
  "job_id":"b2a1-...",
  "status":"done",
  "stats":{
    "documents_added":42,"documents_skipped":11,"chunks":380,
    "duration_ms":18492,"errors":[]
  }
}
```

## `POST /query`

Retrieve chunks for a user question.

```json
{
  "query": "what did we decide about Q4 pricing in the last meeting?",
  "k": 8,
  "hybrid": true,
  "filters": {
    "sources": ["work-notes","email-exports"],
    "mime": ["text/markdown","message/rfc822"],
    "modified_after": "2025-05-01T00:00:00Z"
  },
  "rerank": true,
  "mmr_lambda": 0.5,
  "return_text": true
}
```

**Response**

```json
{
  "query_id": "q-7fb5...",
  "results": [
    {
      "rank": 1,
      "chunk_id": "ch_01e4...",
      "document_id": "doc_9acb...",
      "score": 0.82,                  // post-rerank
      "dense_score": 0.73,
      "sparse_score": 12.4,
      "title": "2025-08-12 sales sync",
      "snippet": "…settled on 10% intro discount for Q4 for EDU…",
      "text": "full chunk text…",
      "provenance": {
        "source_label": "Notes",
        "path": "/Users/arfi/Notes/sales/2025-08-12.md",
        "page_from": null,
        "page_to": null,
        "section": "Q4 Pricing",
        "modified_ts": 1691821000000
      },
      "deep_link": "ctxc://doc/doc_9acb...?chunk=ch_01e4..."
    }
  ]
}
```

## `POST /rerank`

Rerank your own candidates (useful if an external retriever called first).

```json
{
  "query": "kubernetes upgrade steps",
  "candidates": [
    {"id":"a","text":"…"},
    {"id":"b","text":"…"}
  ],
  "model":"cross-encoder/ms-marco-MiniLM-L-6-v2",
  "top_k": 10
}
```

**Response**

```json
{"results":[{"id":"b","score":0.91},{"id":"a","score":0.44}]}
```

## `GET /why/:query_id`

Fetch frozen provenance for a past `/query` (stable across LLM sessions).

```json
{"query_id":"q-7fb5...","results":[{"chunk_id":"...","score":0.82,"provenance":{...}}]}
```

## `POST /upsert_tags`

Attach tags to documents (persisted in `meta_json`).

```json
{"document_ids":["doc_9acb..."],"tags":["Q4","pricing","sales"]}
```

## `POST /delete`

Soft delete by document or source.

```json
{"document_ids":["doc_x"],"source_ids":["src_y"],"hard":false}
```

---

# CLI

```
pipx install context-cache

ctxc sources add --label Notes --kind folder --uri file:///Users/arfi/Notes --include "**/*.{md,txt,pdf}"
ctxc ingest --all
ctxc query "vector db comparison" --k 8 --source Notes --since 2025-01-01
ctxc why q-7fb5...
ctxc export --format jsonl --out ~/Desktop/context_export.jsonl
```

---

# Desktop UI (MVP screens)

1. **Home / Status**

   * Index size, last ingest, active jobs, CPU/GPU usage.
   * “Pause watching” toggle.

2. **Search**

   * Query bar, filters (source/mime/time/tags).
   * Results list → right pane shows full chunk, neighbors, and **“Open source”** button.

3. **Provenance**

   * Timeline of where answer snippets came from; copyable citations.

4. **Settings**

   * Models: embeddings, reranker toggle, dimensions.
   * Sources: add/remove, include/exclude globs.
   * Privacy: “no telemetry”, “opt-in anon stats”.
   * Sync (optional): turn on/off; key management.

---

# Algorithms & nitty-gritty

## Chunking (detailed)

```python
TARGET = 512  # tokens
MAX = 768
MIN = 120

# 1) split on headings (markdown #, ##) and big gaps
segments = split_by_structure(text)

# 2) merge greedily
chunk, count = [], 0
for seg in segments:
    t = tokens(seg)
    if count + t <= MAX:
        chunk.append(seg); count += t
        if count >= TARGET:
            flush(chunk); chunk, count = [], 0
    else:
        if count >= MIN:
            flush(chunk); chunk, count = [], 0
        if t > MAX:
            for piece in split_smart(seg, MAX):
                flush([piece])
        else:
            chunk = [seg]; count = t
if count: flush(chunk)
```

* `split_by_structure` uses headings, paragraph breaks, page breaks.
* `split_smart` breaks on sentences using `spacy`/`nltk`.

## Embedding hygiene

* Use **e5 prompts**:

  * Query → `"query: {q}"`
  * Passage → `"passage: {chunk}"`
* Normalize vectors to unit length; cosine similarity.

## Score mixing (RRF)

```
score = Σ_i 1 / (k_i + rank_i)   # k_i=60 typical
```

## Reranking

* Batch size 16; truncate to 256 tokens per candidate.

## MMR diversification

```
argmax_i [ λ*sim(i, query) - (1-λ)*max_j sim(i, j) ]
```

---

# Privacy & security

* **Local-first:** no network calls unless user enables sync or web connectors.
* **Secret storage:** encryption key saved in OS keychain; DB at rest optionally encrypted (SQLCipher).
* **Sandbox:** when sharing outputs, a **“redact PII”** toggle runs Presidio on returned snippets.
* **Prompt-injection guard** (for when an external LLM uses `/query` results): return **text + provenance** only; **never execute instructions** found in source content. Provide a `safety_notes` field recommending the host LLM to ignore in-document instructions.

---

# Connectors (MVP + near-term)

## MVP

* **Folders** (recursive)
* **MBOX/EML** (export from Gmail/Apple Mail/Outlook)
* **Markdown vaults** (Obsidian-style, read front-matter tags)

## After MVP

* **Google Drive/Docs** (token-scoped, incremental sync)
* **Notion export** (zip)
* **Confluence space export**
* **Slack export** (standard workspace export)

> All online connectors pass through your app and store **only the text + minimal metadata** locally. No vendor writes back.

---

# Performance targets

* 100k chunks on laptop:

  * Dense top-100 ANN: **<80ms**
  * Merge + RRF: **<20ms**
  * Rerank top-50: **\~70–120ms** (optional)
  * End-to-end `/query` (no rerank): **<150ms**, with rerank: **<300ms**
* Ingest: **>30 docs/sec** for plain text; **>2 pages/sec** for PDFs (single thread). Provide `--workers N`.

---

# Config file

`~/.config/context-cache/config.yaml`

```yaml
db_path: ~/.context-cache/cc.db
vectors:
  model: intfloat/e5-small-v2
  dim: 384
  index: sqlite-vss      # or faiss, qdrant
  top_k: 100
rerank:
  enabled: true
  model: cross-encoder/ms-marco-MiniLM-L-6-v2
  top_m: 50
mmr_lambda: 0.5
watch:
  poll_interval_ms: 800
  include_glob: "**/*.{md,txt,pdf,docx,eml,mbox}"
  exclude_glob: "**/{.git,.obsidian,node_modules}/**"
privacy:
  telemetry: false
  redact_pii_by_default: false
sync:
  enabled: false
  provider: "local-encrypted"
```

---

# Integration patterns

## As a “retrieval plugin” for ChatGPT/Copilot/etc.

* Call `/query` first, feed top-k chunks + citations into your LLM prompt.
* Prompt snippet (host app):

```
Use the provided context snippets to answer. 
Only rely on them; if unsure, say so. 
Cite each claim with [#rank] and return "sources" as a list of deep_links.
```

## VS Code extension (simple)

* Webview talks to `http://127.0.0.1:5173/query`.
* Highlighted text → right-click → “Find related docs” (posts the selection as query).
* Result click → opens file at offset.

---

# Testing & eval

## Unit tests

* Extractors: golden PDFs/emails → deterministic text.
* Chunker: input → expected boundaries (run on edge cases like tables).
* Embeddings: deterministic seeds, norm=1.0 ± 1e-6.

## Retrieval eval

* Build a tiny **Q/A gold set** from your notes (20–50 pairs).
* Metrics: top-k recall\@5/10, MRR, latency percentiles.
* CLI: `ctxc eval --qa qa.jsonl`.

---

# Observability

* **/metrics** (Prometheus): ingest rates, index size, query latency histograms.
* **Logs**: JSON lines; per pipeline stage timings and errors.
* **Red light** on UI status if watcher stalled (no FS events in N minutes).

---

# Roadmap (90 days)

1. **v0.1 (Weeks 1–4)** – Local watch → chunk → embed → query; desktop UI; CLI; `/query`.
2. **v0.2 (Weeks 5–8)** – Reranker; hybrids; tags; `/why`; VS Code extension; mbox import.
3. **v0.3 (Weeks 9–12)** – Google Drive connector; encrypted optional sync (between devices); simple sharing of **read-only bundles** (`.ctxcpack` file with vectors+chunks).

---

# Example end-to-end flow (pseudo-code)

```python
# start server
from context_cache import Server
Server(config="~/.config/context-cache/config.yaml").serve(port=5173)

# register a source
POST /sources
{
  "label":"Notes",
  "kind":"folder",
  "uri":"file:///Users/arfi/Notes",
  "include_glob":"**/*.{md,txt,pdf}"
}

# ingest
POST /ingest {"sources":["<src-id>"]}

# query
POST /query {
  "query":"pros and cons of qdrant vs faiss for small indexes",
  "k":6, "hybrid":true, "rerank":true
}

# host LLM uses results
prompt = render_prompt(user_q, results)

# user clicks "Why?"
GET /why/q-7fb5...
```

---

# Acceptance criteria (MVP)

* On macOS/Windows/Linux, after adding a folder, **typing a query returns top-k with paths** in <300ms for 100k chunks.
* PDFs and Markdown supported; MBOX import optional but tested.
* CLI & HTTP API produce identical results for same params.
* Provenance includes: file path/URL, page range or line offsets, section title if any, and a deep link string.
* All writes survive restart; re-ingesting same files does not duplicate rows.
* No network calls occur without explicit connectors enabled.

---

# Stretch ideas (defensible)

* **Personal schema learning**: auto-extract entities you frequently ask about (people, projects) and let you filter by them.
* **Context playlists**: save a set of chunks as a named “bundle” you can pin into any future LLM prompt.
* **On-device reranking with small transformer (ggml/metal)** for speed without Python GIL.
* **Inline summaries**: cache 3–5 sentence summaries per chunk (generated locally) to speed LLM prompts.
* **Temporal weighting**: decay older chunks unless explicitly boosted by tags.

---
