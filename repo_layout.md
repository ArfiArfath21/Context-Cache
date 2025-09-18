# Repo Layout

Monorepo Cookiecutter Structure for Context Cache
```
context-cache/
├─ README.md
├─ LICENSE
├─ Makefile
├─ .gitignore
├─ pyproject.toml
├─ uv.lock                               # if you use uv/pip-tools; optional
├─ .env.example
├─ config/
│  └─ config.example.yaml
├─ backend/
│  ├─ context_cache/
│  │  ├─ __init__.py
│  │  ├─ app.py                          # FastAPI server bootstrap
│  │  ├─ api/
│  │  │  ├─ __init__.py
│  │  │  ├─ routes_ingest.py
│  │  │  ├─ routes_query.py
│  │  │  ├─ routes_admin.py              # sources, delete, tags, health
│  │  │  └─ dependencies.py
│  │  ├─ core/
│  │  │  ├─ config.py
│  │  │  ├─ logging.py
│  │  │  └─ metrics.py                   # Prometheus
│  │  ├─ db/
│  │  │  ├─ __init__.py
│  │  │  ├─ schema.sql
│  │  │  ├─ sqlite.py                    # driver & SQL helpers
│  │  │  └─ migrations/                  # alembic (optional)
│  │  ├─ models/
│  │  │  ├─ dto.py                       # Pydantic models
│  │  │  └─ entities.py                  # dataclasses for internal use
│  │  ├─ ingest/
│  │  │  ├─ watcher.py
│  │  │  ├─ pipeline.py
│  │  │  ├─ loaders.py                   # pdf/docx/mbox/md
│  │  │  ├─ chunker.py
│  │  │  ├─ embeddings.py
│  │  │  └─ dedupe.py
│  │  ├─ retrieval/
│  │  │  ├─ vector_index.py              # sqlite-vss/faiss wrapper
│  │  │  ├─ hybrid.py                    # dense+sparse, RRF, MMR
│  │  │  ├─ rerank.py
│  │  │  └─ search.py                    # orchestrates query flow
│  │  ├─ security/
│  │  │  ├─ encryption.py                # SQLCipher, libsodium helpers
│  │  │  └─ keychain.py                  # OS keyring access
│  │  ├─ utils/
│  │  │  ├─ ids.py                       # UUID/ULID
│  │  │  ├─ time.py
│  │  │  ├─ hashing.py
│  │  │  └─ text.py
│  │  └─ cli/
│  │     └─ main.py                      # `ctxc` CLI (Typer)
│  └─ tests/
│     ├─ conftest.py
│     ├─ test_chunker.py
│     ├─ test_embeddings.py
│     ├─ test_retrieval.py
│     ├─ test_api.py
│     └─ fixtures/
│        ├─ sample.md
│        ├─ mail.mbox
│        └─ small.pdf
└─ desktop/                               # Tauri (Rust) + web UI (Vite + React)
   ├─ src-tauri/
   │  ├─ Cargo.toml
   │  └─ src/main.rs                      # window + system tray, IPC to localhost
   └─ ui/
      ├─ package.json
      ├─ vite.config.ts
      └─ src/
         ├─ main.tsx
         ├─ App.tsx
         ├─ pages/{Status,Search,Settings}.tsx
         └─ components/{ResultList,Filters,Provenance}.tsx
```
