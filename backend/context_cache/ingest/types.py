"""Common ingestion data structures."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


@dataclass(slots=True)
class LoadedDocument:
    """Represents a document extracted from a source."""

    path: Path
    text: str
    raw_bytes: bytes | None
    metadata: dict[str, Any]
    mime: str
    title: str | None
    author: str | None
    created_ts: int | None
    modified_ts: int | None
    size_bytes: int


@dataclass(slots=True)
class ChunkPayload:
    """Chunk produced by the chunker prior to persistence."""

    id: str
    document_id: str
    ordinal: int
    start_char: int
    end_char: int
    text: str
    token_count: int
    metadata: dict[str, Any]


@dataclass(slots=True)
class EmbeddingPayload:
    """Embedding ready to be stored."""

    chunk_id: str
    model: str
    dim: int
    vector: bytes
    style: str = "dense"


@dataclass(slots=True)
class IngestStats:
    """Aggregated ingest statistics."""

    processed: int = 0
    skipped: int = 0
    failed: int = 0
    chunks: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "processed": self.processed,
            "skipped": self.skipped,
            "failed": self.failed,
            "chunks": self.chunks,
        }


@dataclass(slots=True)
class IngestResult:
    """Outcome for a single processed path."""

    document_id: str | None
    path: Path
    status: str
    detail: str | None = None
    chunks: Sequence[ChunkPayload] | None = None


__all__ = [
    "LoadedDocument",
    "ChunkPayload",
    "EmbeddingPayload",
    "IngestStats",
    "IngestResult",
]
