"""Internal dataclasses representing persisted entities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Source:
    id: str
    kind: str
    uri: str
    label: str | None
    include_glob: str | None
    exclude_glob: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class Document:
    id: str
    source_id: str
    external_id: str | None
    title: str | None
    author: str | None
    created_ts: int | None
    modified_ts: int | None
    mime: str | None
    sha256: str
    raw_bytes: bytes | None
    text: str | None
    meta_json: dict[str, Any] | None
    size_bytes: int | None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class Chunk:
    id: str
    document_id: str
    ordinal: int
    start_char: int
    end_char: int
    text: str
    token_count: int
    meta_json: dict[str, Any] | None
    created_at: datetime


@dataclass(slots=True)
class Embedding:
    chunk_id: str
    model: str
    dim: int
    vector: bytes
    style: str
    created_at: datetime
