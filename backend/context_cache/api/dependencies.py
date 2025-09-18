"""Shared FastAPI dependencies."""

from __future__ import annotations

from functools import lru_cache

from context_cache.core.config import Settings, get_settings
from context_cache.db.sqlite import SQLiteDatabase
from context_cache.ingest.embeddings import EmbeddingModel
from context_cache.ingest.pipeline import IngestPipeline
from context_cache.retrieval import QueryService, VectorIndex
from context_cache.retrieval.rerank import Reranker

_DB: SQLiteDatabase | None = None
_VECTOR_INDEX: VectorIndex | None = None
_PIPELINE: IngestPipeline | None = None
_QUERY_SERVICE: QueryService | None = None


@lru_cache(maxsize=1)
def get_app_settings() -> Settings:
    return get_settings()


def get_database() -> SQLiteDatabase:
    global _DB
    if _DB is None:
        settings = get_app_settings()
        db = SQLiteDatabase(settings.db_path)
        db.ensure_schema()
        _DB = db
    return _DB


def get_embedding_model() -> EmbeddingModel:
    settings = get_app_settings()
    return EmbeddingModel.get(settings.embedding_model)


def get_vector_index() -> VectorIndex:
    global _VECTOR_INDEX
    if _VECTOR_INDEX is None:
        settings = get_app_settings()
        db = get_database()
        embedding_model = get_embedding_model()
        index = VectorIndex(dim=embedding_model.dim, use_faiss=settings.use_faiss)
        index.rebuild(db, settings.embedding_model)
        _VECTOR_INDEX = index
    return _VECTOR_INDEX


def get_ingest_pipeline() -> IngestPipeline:
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = IngestPipeline(
            database=get_database(),
            settings=get_app_settings(),
            embedding_model=get_embedding_model(),
            vector_index=get_vector_index(),
        )
    return _PIPELINE


def get_query_service() -> QueryService:
    global _QUERY_SERVICE
    if _QUERY_SERVICE is None:
        _QUERY_SERVICE = QueryService(
            db=get_database(),
            settings=get_app_settings(),
            vector_index=get_vector_index(),
            embedding_model=get_embedding_model(),
            reranker=Reranker(get_app_settings().rerank_model),
        )
    return _QUERY_SERVICE


__all__ = [
    "get_app_settings",
    "get_database",
    "get_ingest_pipeline",
    "get_query_service",
    "get_embedding_model",
    "get_vector_index",
]
