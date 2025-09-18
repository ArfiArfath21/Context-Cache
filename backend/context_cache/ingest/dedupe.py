"""Deduplication helpers."""

from __future__ import annotations

from typing import Iterable, Tuple

from context_cache.ingest.types import LoadedDocument
from context_cache.utils.hashing import sha256_bytes


def dedupe_hashes(hashes: Iterable[str]) -> list[str]:
    """Remove duplicates while preserving order."""
    seen: set[str] = set()
    unique: list[str] = []
    for item in hashes:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def document_hash(document: LoadedDocument) -> str:
    """Compute a stable hash for a loaded document."""
    payload = document.raw_bytes or document.text.encode("utf-8")
    return sha256_bytes(payload)


def dedupe_documents(documents: Iterable[LoadedDocument]) -> list[Tuple[LoadedDocument, str]]:
    """Return unique documents along with their hash."""
    seen: set[str] = set()
    unique: list[Tuple[LoadedDocument, str]] = []
    for document in documents:
        digest = document_hash(document)
        if digest in seen:
            continue
        seen.add(digest)
        unique.append((document, digest))
    return unique


__all__ = ["dedupe_hashes", "document_hash", "dedupe_documents"]
