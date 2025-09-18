# Context Cache - Build Guide

Here’s **Python function signatures**, and a **complete OpenAPI 3.1 spec** for you to build.

# Build & run

### `pyproject.toml` (minimal)

```toml
[project]
name = "context-cache"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.111",
  "uvicorn[standard]>=0.29",
  "pydantic>=2.7",
  "python-multipart",
  "watchdog>=4.0",
  "pymupdf>=1.24",
  "python-docx>=1.1",
  "markdown-it-py>=3.0",
  "textract==1.6.5",            # or replace with custom extractors
  "sentence-transformers>=3.0",
  "faiss-cpu>=1.8.0",            # OR sqlite-vss (see below)
  "numpy>=1.26",
  "scikit-learn>=1.5",
  "rank-bm25>=0.2.2",
  "rapidfuzz>=3.9",
  "tiktoken>=0.7",
  "sqlalchemy>=2.0",
  "sqlite-utils>=3.36",
  "prometheus-client>=0.20",
  "typer>=0.12",
  "pyyaml>=6.0",
  "orjson>=3.10",
  "langid==1.1.6",
  "presidio-analyzer>=2.2"
]

[project.optional-dependencies]
sqlite-vss = ["sqlite-vss==0.1.3"]      # if you choose sqlite-vss
dev = ["pytest>=8.3", "httpx>=0.27", "pytest-asyncio>=0.23", "ruff>=0.5"]

[tool.ruff]
line-length = 100
```

### `Makefile`

```makefile
.PHONY: dev api test fmt

dev: ## run backend dev server
\tuvicorn context_cache.app:app --reload --port 5173

api: ## print OpenAPI
\tpython -c "from context_cache.app import app; import json; print(app.openapi_json())"

test:
\tpytest -q

fmt:
\truff check --fix .
```

---

# Key Python function signatures (docstrings included)

> These are deliberately tight and “hand-off friendly”. Codex can implement from here.

### `backend/context_cache/app.py`

```python
from fastapi import FastAPI
from context_cache.api.routes_ingest import router as ingest_router
from context_cache.api.routes_query import router as query_router
from context_cache.api.routes_admin import router as admin_router
from context_cache.core.config import Settings

settings = Settings()  # loads YAML + env

app = FastAPI(
    title="Context Cache",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(ingest_router, prefix="/ingest", tags=["ingest"])
app.include_router(query_router, prefix="/", tags=["query"])
app.include_router(admin_router, prefix="/", tags=["admin"])

@app.get("/health", tags=["admin"])
def health() -> dict:
    """Liveness check."""
    return {"ok": True}
```

### `core/config.py`

```python
from pydantic import BaseModel
from pathlib import Path

class Settings(BaseModel):
    db_path: Path = Path.home() / ".context-cache" / "cc.db"
    use_faiss: bool = True
    embedding_model: str = "intfloat/e5-small-v2"
    rerank_enabled: bool = True
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    mmr_lambda: float = 0.5
    top_k_dense: int = 100
    top_k_final: int = 8
    watch_include: str = "**/*.{md,txt,pdf,docx,eml,mbox}"
    watch_exclude: str = "**/{.git,.obsidian,node_modules}/**"

    @classmethod
    def from_yaml(cls, path: Path | None = None) -> "Settings":
        """Load YAML config and overlay env vars; fall back to defaults."""
```

### `db/sqlite.py`

```python
import sqlite3
from pathlib import Path
from typing import Iterable, Any

def connect(db_path: Path) -> sqlite3.Connection:
    """Return a connection with pragmas set for WAL and performance."""
def exec_script(conn: sqlite3.Connection, script_path: Path) -> None:
    """Execute schema.sql (idempotent)."""
def upsert_document(conn, doc) -> str:
    """Insert or update a document row; returns document_id."""
def insert_chunks(conn, document_id: str, chunks: list[dict]) -> None:
    """Bulk insert chunk rows."""
def search_fts(conn, query: str, limit: int) -> list[tuple]:
    """FTS5 sparse search; returns [(rowid, score, payload...), ...]."""
```

### `ingest/loaders.py`

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class LoadedDoc:
    text: str
    meta: dict
    mime: str
    title: str | None
    bytes: bytes | None

def load_any(path: Path) -> LoadedDoc:
    """Dispatch to specific loader based on extension/MIME."""
def load_pdf(path: Path) -> LoadedDoc: ...
def load_md(path: Path) -> LoadedDoc: ...
def load_docx(path: Path) -> LoadedDoc: ...
def load_eml(path: Path) -> LoadedDoc: ...
def load_mbox(path: Path) -> list[LoadedDoc]:
    """Return one LoadedDoc per email."""
```

### `ingest/chunker.py`

```python
from typing import Iterable

def chunk_text(
    text: str,
    target_tokens: int = 512,
    max_tokens: int = 768,
    min_tokens: int = 120,
) -> list[dict]:
    """
    Split text into chunks preserving paragraph/section boundaries.
    Returns list of dicts with keys:
      - text
      - start_char, end_char
      - token_count
      - meta (section/page hints)
    """
```

### `ingest/embeddings.py`

```python
import numpy as np
from typing import Iterable

class Embedder:
    def __init__(self, model_name: str = "intfloat/e5-small-v2") -> None: ...
    def encode_passages(self, texts: list[str], batch_size: int = 64) -> np.ndarray:
        """Return L2-normalized embeddings (N, D)."""
    def encode_queries(self, texts: list[str], batch_size: int = 64) -> np.ndarray:
        """Apply 'query:' prefix per e5 convention and return normalized vectors."""
```

### `retrieval/vector_index.py`

```python
import numpy as np
from typing import Sequence

class VectorIndex:
    def __init__(self, dim: int, backend: str = "faiss", db_path: str | None = None) -> None: ...
    def upsert(self, ids: Sequence[str], vectors: np.ndarray) -> None:
        """Add or update vectors for chunk ids."""
    def search(self, query_vec: np.ndarray, k: int) -> list[tuple[str, float]]:
        """Return [(chunk_id, score)] with cosine similarity."""
```

### `retrieval/hybrid.py`

```python
def rrf_merge(
    dense: list[tuple[str, float]],
    sparse: list[tuple[str, float]],
    k: int = 8,
    k_rrf: int = 60,
) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion between two ranked lists."""

def mmr(
    query_vec, candidates: list[tuple[str, float, str]], lambda_: float = 0.5, k: int = 8
) -> list[tuple[str, float, str]]:
    """MMR diversification on candidates (id, sim, doc_id)."""
```

### `retrieval/rerank.py`

```python
from typing import Sequence

class CrossEncoderReranker:
    def __init__(self, model_name: str): ...
    def rerank(self, query: str, candidates: Sequence[dict], top_m: int = 50) -> list[dict]:
        """
        candidates: [{"id": chunk_id, "text": "..."}]
        returns: [{"id": chunk_id, "score": float}]
        """
```

### `retrieval/search.py`

```python
from typing import Any

def retrieve(
    query: str,
    filters: dict[str, Any] | None,
    k_final: int,
    use_hybrid: bool,
    use_rerank: bool,
) -> dict:
    """
    Orchestrates dense + sparse retrieval, optional rerank, MMR diversification.
    Returns JSON-ready dict with results, scores, and provenance.
    """
```

### `api/routes_query.py`

```python
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class QueryRequest(BaseModel):
    query: str
    k: int = 8
    hybrid: bool = True
    filters: dict | None = None
    rerank: bool = True
    mmr_lambda: float = 0.5
    return_text: bool = True

@router.post("/query")
def post_query(req: QueryRequest) -> dict:
    """Run retrieval and return top-k with provenance; logs a query_id."""
```

### `api/routes_ingest.py`

```python
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class IngestRequest(BaseModel):
    sources: list[str] | None = None
    paths: list[str] | None = None
    include_glob: str | None = None
    exclude_glob: str | None = None
    priority: str = "normal"

@router.post("")
def trigger_ingest(req: IngestRequest) -> dict:
    """Queue an ingest job and return job_id."""
```

### `api/routes_admin.py`

```python
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class SourceCreate(BaseModel):
    label: str
    kind: str
    uri: str
    include_glob: str | None = None
    exclude_glob: str | None = None

@router.post("/sources")
def add_source(src: SourceCreate) -> dict: ...

@router.post("/upsert_tags")
def upsert_tags(body: dict) -> dict: ...

@router.post("/delete")
def soft_delete(body: dict) -> dict: ...

@router.get("/why/{query_id}")
def why(query_id: str) -> dict: ...
```

---

# OpenAPI 3.1 (drop-in)

> Save as `openapi.yaml`. Paths mirror the spec we discussed. It’s strict enough for codegen.

```yaml
openapi: 3.1.0
info:
  title: Context Cache
  version: "0.1.0"
  summary: Local retrieval (RAG) API with provenance
servers:
  - url: http://127.0.0.1:5173
paths:
  /health:
    get:
      tags: [admin]
      summary: Liveness check
      responses:
        "200":
          description: OK
          content:
            application/json:
              schema:
                type: object
                properties:
                  ok: { type: boolean }
  /sources:
    post:
      tags: [admin]
      summary: Register a new source
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/SourceCreate"
      responses:
        "200":
          description: Created
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Source"
  /ingest:
    post:
      tags: [ingest]
      summary: Trigger an ingest job
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/IngestRequest"
      responses:
        "200":
          description: Job queued
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/IngestJobRef"
  /ingest/{job_id}:
    get:
      tags: [ingest]
      summary: Get ingest job status
      parameters:
        - in: path
          name: job_id
          required: true
          schema: { type: string }
      responses:
        "200":
          description: Job status
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/IngestJobStatus"
  /query:
    post:
      tags: [query]
      summary: Retrieve chunks for a user question
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/QueryRequest"
      responses:
        "200":
          description: Query results
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/QueryResponse"
  /rerank:
    post:
      tags: [query]
      summary: Rerank caller-supplied candidates
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/RerankRequest"
      responses:
        "200":
          description: Rerank results
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/RerankResponse"
  /why/{query_id}:
    get:
      tags: [query]
      summary: Fetch frozen provenance for a past query
      parameters:
        - in: path
          name: query_id
          required: true
          schema: { type: string }
      responses:
        "200":
          description: Provenance details
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/WhyResponse"
  /upsert_tags:
    post:
      tags: [admin]
      summary: Attach tags to documents
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/UpsertTagsRequest"
      responses:
        "200":
          description: OK
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/UpsertTagsResponse"
  /delete:
    post:
      tags: [admin]
      summary: Soft delete by document or source
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/DeleteRequest"
      responses:
        "200":
          description: OK
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/DeleteResponse"
components:
  schemas:
    SourceCreate:
      type: object
      required: [label, kind, uri]
      properties:
        label: { type: string }
        kind:
          type: string
          enum: [folder, mbox, eml, markdown, notion_export, other]
        uri: { type: string, description: "file:// or other scheme" }
        include_glob: { type: string, nullable: true }
        exclude_glob: { type: string, nullable: true }
    Source:
      allOf:
        - $ref: "#/components/schemas/SourceCreate"
        - type: object
          properties:
            id: { type: string }
            created_at: { type: string, format: date-time }
            updated_at: { type: string, format: date-time }
    IngestRequest:
      type: object
      properties:
        sources:
          type: array
          items: { type: string }
          description: "Source IDs to ingest"
        paths:
          type: array
          items: { type: string }
          description: "Direct file/folder paths"
        include_glob: { type: string, nullable: true }
        exclude_glob: { type: string, nullable: true }
        priority:
          type: string
          enum: [low, normal, high]
          default: normal
    IngestJobRef:
      type: object
      properties:
        job_id: { type: string }
        status: { type: string, enum: [queued, running, done, error] }
    IngestJobStatus:
      allOf:
        - $ref: "#/components/schemas/IngestJobRef"
        - type: object
          properties:
            stats:
              type: object
              properties:
                documents_added: { type: integer }
                documents_skipped: { type: integer }
                chunks: { type: integer }
                duration_ms: { type: integer }
                errors:
                  type: array
                  items: { type: string }
    QueryRequest:
      type: object
      required: [query]
      properties:
        query: { type: string }
        k: { type: integer, default: 8, minimum: 1, maximum: 50 }
        hybrid: { type: boolean, default: true }
        filters:
          type: object
          additionalProperties: true
          description: "source/mime/time/tags filters"
        rerank: { type: boolean, default: true }
        mmr_lambda: { type: number, default: 0.5, minimum: 0, maximum: 1 }
        return_text: { type: boolean, default: true }
    QueryResponse:
      type: object
      properties:
        query_id: { type: string }
        results:
          type: array
          items:
            $ref: "#/components/schemas/ResultItem"
    ResultItem:
      type: object
      properties:
        rank: { type: integer }
        chunk_id: { type: string }
        document_id: { type: string }
        score: { type: number }
        dense_score: { type: number, nullable: true }
        sparse_score: { type: number, nullable: true }
        title: { type: string, nullable: true }
        snippet: { type: string, nullable: true }
        text: { type: string, nullable: true }
        provenance:
          type: object
          properties:
            source_label: { type: string, nullable: true }
            path: { type: string, nullable: true }
            page_from: { type: integer, nullable: true }
            page_to: { type: integer, nullable: true }
            section: { type: string, nullable: true }
            modified_ts: { type: integer, nullable: true }
        deep_link: { type: string }
    RerankRequest:
      type: object
      required: [query, candidates]
      properties:
        query: { type: string }
        candidates:
          type: array
          items:
            type: object
            required: [id, text]
            properties:
              id: { type: string }
              text: { type: string }
        model: { type: string, default: "cross-encoder/ms-marco-MiniLM-L-6-v2" }
        top_k: { type: integer, default: 10 }
    RerankResponse:
      type: object
      properties:
        results:
          type: array
          items:
            type: object
            properties:
              id: { type: string }
              score: { type: number }
    WhyResponse:
      type: object
      properties:
        query_id: { type: string }
        results:
          type: array
          items:
            type: object
            properties:
              chunk_id: { type: string }
              score: { type: number }
              provenance:
                type: object
                additionalProperties: true
    UpsertTagsRequest:
      type: object
      properties:
        document_ids:
          type: array
          items: { type: string }
        tags:
          type: array
          items: { type: string }
    UpsertTagsResponse:
      type: object
      properties:
        updated: { type: integer }
    DeleteRequest:
      type: object
      properties:
        document_ids:
          type: array
          items: { type: string }
        source_ids:
          type: array
          items: { type: string }
        hard: { type: boolean, default: false }
    DeleteResponse:
      type: object
      properties:
        status: { type: string }
```

---

# Minimal CLI (Typer) skeleton

```python
# backend/context_cache/cli/main.py
import typer, requests, json, os

app = typer.Typer(name="ctxc")

HOST = os.environ.get("CTXC_HOST", "http://127.0.0.1:5173")

@app.command()
def ingest(all: bool = typer.Option(False, help="Ingest all sources"),
           path: str | None = None):
    """Trigger ingest."""
    body = {"sources": None, "paths": [path] if path else None}
    r = requests.post(f"{HOST}/ingest", json=body, timeout=60)
    typer.echo(r.json())

@app.command()
def query(q: str, k: int = 8):
    """Query top-k."""
    r = requests.post(f"{HOST}/query", json={"query": q, "k": k}, timeout=60)
    typer.echo(json.dumps(r.json(), indent=2))

if __name__ == "__main__":
    app()
```

---

# Test scaffolding

```python
# backend/tests/test_chunker.py
from context_cache.ingest.chunker import chunk_text

def test_chunk_boundaries_basic():
    text = "Title\n\nPara1.\n\nPara2 is longer..." * 10
    chunks = chunk_text(text, target_tokens=50, max_tokens=80, min_tokens=10)
    assert chunks, "Should produce chunks"
    assert all(c["start_char"] < c["end_char"] for c in chunks)
```

```python
# backend/tests/test_api.py
import asyncio, httpx, pytest
from context_cache.app import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
```

---

# Desktop (Tauri) notes

* The desktop app just **talks to localhost** (`http://127.0.0.1:5173`).
* Add a small tray with: **Start/Pause watcher**, **Ingest now**, **Open UI**.
* IPC commands: optional; you can stick to HTTP.
* React pages:

  * **Status**: shows `/health`, index size via `/metrics` (add later).
  * **Search**: POST `/query`, render result list; clicking a result opens file path via Tauri `shell::open()` with `path#char=<start>-<end>` anchor where possible.
  * **Settings**: forms to add `/sources`, toggle rerank, set filters.

---

# What to code next (fast path)

1. Implement **schema.sql** and `db/sqlite.py` helpers.
2. Implement **embeddings.py** (loading and caching the model).
3. Implement **vector\_index.py** with FAISS (flat/IP) to start.
4. Wire **/query** → `retrieve()` → return JSON exactly like `QueryResponse`.
5. Implement **loaders + chunker** for md/pdf to unblock ingest.
6. Backfill **/sources**, **/ingest** (even if ingest is synchronous at first).
