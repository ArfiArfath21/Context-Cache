"""Embedding utilities."""

from __future__ import annotations

import hashlib
import logging
import math
import re
from array import array
from dataclasses import dataclass
from typing import Iterable, List

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"\w+")


@dataclass(slots=True)
class EmbeddingBatch:
    vectors: list[list[float]]
    model: str
    dim: int
    backend: str


class EmbeddingModel:
    """Lightweight hashed embedding model with deterministic output."""

    _instances: dict[str, "EmbeddingModel"] = {}

    def __init__(
        self,
        model_name: str,
        dim: int = 384,
    ) -> None:
        self.model_name = model_name
        self._dim = dim
        self._backend = "hashed"

    @classmethod
    def get(cls, model_name: str) -> "EmbeddingModel":
        key = model_name or "hashed"
        if key not in cls._instances:
            cls._instances[key] = EmbeddingModel(model_name=key)
        return cls._instances[key]

    @property
    def dim(self) -> int:
        return self._dim

    @property
    def backend(self) -> str:
        return self._backend

    def encode(self, texts: Iterable[str], batch_size: int = 16) -> EmbeddingBatch:
        vectors: list[list[float]] = []
        for text in texts:
            tokens = _tokenize(text)
            vector = [0.0] * self._dim
            for token in tokens:
                slot = _hash_token(token, self._dim)
                vector[slot] += 1.0
            _normalize(vector)
            vectors.append(vector)
        return EmbeddingBatch(vectors=vectors, model=self.model_name, dim=self._dim, backend=self._backend)

    def as_bytes(self, vector: list[float]) -> bytes:
        arr = array("f", vector)
        return arr.tobytes()


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _hash_token(token: str, dim: int) -> int:
    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
    value = int.from_bytes(digest, "big")
    return value % dim


def _normalize(vector: list[float]) -> None:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return
    inv = 1.0 / norm
    for idx, value in enumerate(vector):
        vector[idx] = value * inv


__all__ = ["EmbeddingModel", "EmbeddingBatch"]
