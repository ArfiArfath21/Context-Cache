"""FastAPI application setup for Context Cache."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from context_cache.api.dependencies import (
    get_app_settings,
    get_database,
    get_embedding_model,
    get_ingest_pipeline,
    get_query_service,
    get_vector_index,
)
from context_cache.api.routes_admin import router as admin_router
from context_cache.api.routes_ingest import router as ingest_router
from context_cache.api.routes_query import router as query_router
from context_cache.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title="Context Cache",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        "tauri://localhost",
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(ingest_router, prefix="/ingest", tags=["ingest"])
app.include_router(query_router, prefix="", tags=["query"])
app.include_router(admin_router, prefix="", tags=["admin"])


@app.on_event("startup")
async def startup() -> None:
    """Warm up core singletons on startup."""
    get_app_settings()
    get_database()
    get_embedding_model()
    get_vector_index()
    get_ingest_pipeline()
    get_query_service()


@app.get("/health", tags=["admin"])
def health() -> dict[str, bool]:
    """Simple liveness check."""
    return {"ok": True}
