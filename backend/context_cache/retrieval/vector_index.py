"""Vector index abstraction."""

from __future__ import annotations

from array import array
from dataclasses import dataclass
from typing import Iterable, Sequence

from context_cache.db.sqlite import SQLiteDatabase


@dataclass(slots=True)
class SearchResult:
    chunk_id: str
    score: float


class VectorIndex:
    """Simple in-memory vector index using cosine similarity."""

    def __init__(self, dim: int, use_faiss: bool = False) -> None:  # use_faiss retained for compatibility
        self.dim = dim
        self._ids: list[str] = []
        self._vectors: list[list[float]] = []

    @property
    def size(self) -> int:
        return len(self._vectors)

    def upsert(self, ids: Sequence[str], vectors: Sequence[Sequence[float]]) -> None:
        if not ids:
            return
        for vector in vectors:
            if len(vector) != self.dim:
                raise ValueError("Vector dimension mismatch")
        self._ids.extend(ids)
        self._vectors.extend([list(vector) for vector in vectors])

    def search(self, vector: Sequence[float], top_k: int = 8) -> list[SearchResult]:
        if not self._vectors:
            return []
        if len(vector) != self.dim:
            raise ValueError("Query vector dimension mismatch")
        scores = [
            (idx, _dot(self._vectors[idx], vector))
            for idx in range(len(self._vectors))
        ]
        scores.sort(key=lambda item: item[1], reverse=True)
        limit = min(top_k, len(scores))
        return [SearchResult(chunk_id=self._ids[idx], score=score) for idx, score in scores[:limit]]

    def rebuild(self, db: SQLiteDatabase, model: str) -> None:
        rows = db.query("SELECT chunk_id, vector FROM embeddings WHERE model = ?", [model])
        self._ids = []
        self._vectors = []
        for row in rows:
            vector_bytes = row["vector"]
            floats = array("f")
            floats.frombytes(vector_bytes)
            self._ids.append(row["chunk_id"])
            self._vectors.append(list(floats))
        if self._vectors:
            self.dim = len(self._vectors[0])


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


__all__ = ["VectorIndex", "SearchResult"]
