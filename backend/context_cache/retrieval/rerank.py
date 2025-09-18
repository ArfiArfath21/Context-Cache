"""Reranking helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, Sequence

try:
    from rapidfuzz import fuzz
except Exception:  # pragma: no cover - fallback when rapidfuzz unavailable
    fuzz = None

try:  # pragma: no cover - optional dependency
    from sentence_transformers import CrossEncoder
except Exception:  # pragma: no cover - fallback when dependency missing
    CrossEncoder = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RerankResult:
    chunk_id: str
    score: float


class Reranker:
    """Wrapper around CrossEncoder with deterministic fallback."""

    def __init__(self, model_name: str, device: str | None = None) -> None:
        self.model_name = model_name
        self.device = device
        self._model: CrossEncoder | None = None
        self._load()

    def rerank(self, query: str, candidates: Sequence[dict], top_k: int | None = None) -> list[dict]:
        if not candidates:
            return []
        limit = top_k or len(candidates)
        subset = list(candidates)[:limit]
        if self._model is not None:
            inputs = [[query, candidate["text"]] for candidate in subset]
            scores = self._model.predict(inputs, convert_to_numpy=True)
            ranked = _order_by_scores(subset, scores)
        else:
            ranked = _fallback_rerank(query, subset)
        ranked.extend(candidate for candidate in candidates if candidate not in ranked)
        return ranked[:limit]

    def _load(self) -> None:
        if CrossEncoder is None:
            logger.warning("CrossEncoder unavailable; using fuzzy fallback reranker")
            return
        try:
            self._model = CrossEncoder(self.model_name, device=self.device)
        except Exception as exc:  # pragma: no cover - requires network
            logger.warning("Failed to load rerank model '%s': %s", self.model_name, exc)
            self._model = None


def should_rerank(enabled: bool, override: bool | None) -> bool:
    if override is not None:
        return override
    return enabled


def _order_by_scores(candidates: Sequence[dict], scores: np.ndarray) -> list[dict]:
    scores = list(scores)
    ranked: list[dict] = []
    indexed_scores = sorted(enumerate(scores), key=lambda item: float(item[1]), reverse=True)
    for idx, score in indexed_scores:
        candidate = candidates[int(idx)]
        ranked.append({**candidate, "rerank_score": float(score)})
    return ranked


def _fallback_rerank(query: str, candidates: Sequence[dict]) -> list[dict]:
    scored = []
    for candidate in candidates:
        if fuzz is None:
            score = _fallback_similarity(query, candidate["text"])
        else:
            score = fuzz.token_set_ratio(query, candidate["text"]) / 100.0
        scored.append({**candidate, "rerank_score": score})
    return sorted(scored, key=lambda item: item["rerank_score"], reverse=True)


__all__ = ["Reranker", "should_rerank", "RerankResult"]
