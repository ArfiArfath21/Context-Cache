"""Pydantic DTOs exposed via API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class SourceCreateRequest(BaseModel):
    label: str | None = None
    kind: Literal["folder", "file", "mbox", "markdown", "notion_export", "other"] = "folder"
    uri: str
    include_glob: str | None = None
    exclude_glob: str | None = None


class SourceUpdateRequest(BaseModel):
    label: str | None = None
    include_glob: str | None = None
    exclude_glob: str | None = None


class SourceResponse(SourceCreateRequest):
    id: str
    created_at: datetime
    updated_at: datetime


class IngestRequest(BaseModel):
    sources: list[str] | None = Field(default=None, description="List of source IDs to ingest")
    paths: list[str] | None = Field(default=None, description="Explicit filesystem paths")
    all: bool = Field(default=False, description="Ingest all registered sources")


class IngestResponse(BaseModel):
    job_id: str
    stats: dict[str, int]
    results: list[dict[str, Any]]


class QueryFilters(BaseModel):
    source_ids: list[str] | None = None
    document_ids: list[str] | None = None
    tags: list[str] | None = None


class QueryRequest(BaseModel):
    query: str
    k: int = Field(default=8, ge=1, le=50)
    rerank: bool | None = None
    hybrid: bool | None = None
    filters: QueryFilters | None = None


class ChunkResult(BaseModel):
    chunk_id: str
    document_id: str
    score: float
    text: str
    start_char: int
    end_char: int
    provenance: dict[str, Any]


class QueryResponse(BaseModel):
    query_id: str
    results: list[ChunkResult]


class WhyResponse(BaseModel):
    query_id: str
    results: list[ChunkResult]


class DeleteRequest(BaseModel):
    document_ids: list[str] | None = None
    source_ids: list[str] | None = None
    hard: bool = False


class DeleteResponse(BaseModel):
    status: Literal["ok", "noop"]
    deleted: int


class UpsertTagsRequest(BaseModel):
    document_ids: list[str]
    tags: list[str]


class UpsertTagsResponse(BaseModel):
    updated: int


__all__ = [
    "SourceCreateRequest",
    "SourceUpdateRequest",
    "SourceResponse",
    "IngestRequest",
    "IngestResponse",
    "QueryRequest",
    "QueryResponse",
    "ChunkResult",
    "WhyResponse",
    "DeleteRequest",
    "DeleteResponse",
    "UpsertTagsRequest",
    "UpsertTagsResponse",
]
