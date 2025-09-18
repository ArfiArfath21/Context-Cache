# Context Cache

Context Cache is a local-first knowledge layer that watches your files, builds a private retrieval index, and exposes a friendly API, CLI, and desktop experience for querying your own data.

## Features

- 📥 **Ingestion pipeline** for Markdown, plain text, DOCX, EML/MBOX, and PDF (via PyMuPDF when available)
- 🧩 **Chunking + embeddings** with deterministic hashed embeddings (no external downloads required)
- 🔎 **Hybrid retrieval & reranking** with BM25 fallbacks, MMR diversification, and provenance metadata
- 🖥️ **FastAPI backend** with routes for ingest, query, sources, tags, and health
- 💻 **Typer CLI** (`ctxc`) mirroring the API (`ctxc ingest`, `ctxc query`, `ctxc sources add/list`)
- 🪟 **Tauri desktop app** with React UI, light/dark themes, system tray shortcuts, and status/search/settings pages
- ✅ **Test suite** covering chunking, embeddings, retrieval, and API flows (see `pytest`)

## Repository layout

```
backend/
  context_cache/    # FastAPI app, pipeline, retrieval, utils
  tests/            # Pytest suite with fixtures and API tests
config/
  config.example.yaml
desktop/
  src-tauri/        # Tauri Rust project (system tray, commands)
  ui/               # React + Vite frontend
```

## Getting started

### Prerequisites

- Python 3.11+
- Node.js 18+ (for the desktop UI)
- Rust toolchain + Tauri prerequisites (only if you plan to build the desktop app)

### Backend setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp config/config.example.yaml ~/.config/context-cache/config.yaml  # optional overrides
```

Run the API:

```bash
make dev
```

Available endpoints:

- `POST /ingest` – trigger ingestion for paths or sources
- `POST /query` – retrieve top-k chunks (`rerank`, `hybrid`, `filters` supported)
- `GET /sources` / `POST /sources` – manage registered sources
- `POST /delete` – soft/hard delete documents
- `POST /tags/upsert` – assign tags to documents
- `GET /why/{query_id}` – view stored provenance for a previous query
- `GET /metrics` – Prometheus metrics (fallback no-op if `prometheus-client` missing)

### Command line (ctxc)

```bash
ctxc ingest --path ~/Notes
ctxc ingest --source src_abcdef
ctxc query "project roadmap" --k 6 --no-rerank
ctxc sources list
ctxc sources add ~/Documents --label "Docs"
```

Set `CTXC_HOST` to point to a remote backend if needed.

### Desktop app

Build prerequisites (macOS/Linux):

```bash
cd desktop/ui
npm install
npm run build

cd ../src-tauri
cargo tauri build
```

During development run the Vite dev server (`npm run dev`) and in another terminal `cargo tauri dev`.

The tray menu includes shortcuts for opening the UI and triggering ingestion.

### Tests & quality

Run the backend tests:

```bash
pytest -q
```

Format/lint:

```bash
make fmt
```

### Configuration quick reference

- `CTXC_DB_PATH` – location of the SQLite database (default `~/.context-cache/cc.db`)
- `CTXC_HOST` – backend host for CLI and desktop app (default `http://127.0.0.1:5173`)
- Additional knobs available via `config/config.example.yaml`

## Notes

- The embedding pipeline uses a deterministic hashed embedding to avoid network downloads; swap in Sentence Transformers by adjusting `EmbeddingModel` if you have local models available.
- PDF ingestion depends on PyMuPDF (`pymupdf`). If unavailable the loader will raise a helpful error; other loaders continue to work.
- Metrics gracefully degrade when `prometheus-client` is not installed.

Enjoy running your own private retrieval layer! 🚀
