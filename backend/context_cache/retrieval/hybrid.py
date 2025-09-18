"""Hybrid search utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Sequence, Tuple

try:  # pragma: no cover - optional dependency
    from rank_bm25 import BM25Okapi
except Exception:  # pragma: no cover - fallback when rank_bm25 unavailable
    BM25Okapi = None  # type: ignore

try:  # pragma: no cover - optional dependency
    from rapidfuzz import fuzz
except Exception:  # pragma: no cover - fallback when rapidfuzz unavailable
    fuzz = None  # type: ignore


@dataclass(slots=True)
class RankedItem:
    identifier: str
    score: float


def reciprocal_rank_fusion(results: Sequence[Sequence[Tuple[str, float]]], weight: float = 60.0) -> list[RankedItem]:
    """Combine rankings using reciprocal rank fusion."""
    scores: dict[str, float] = {}
    for hits in results:
        for rank, (chunk_id, _) in enumerate(hits, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (weight + rank)
    fused = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [RankedItem(identifier=chunk_id, score=score) for chunk_id, score in fused]


def bm25_rank(query: str, documents: Sequence[Tuple[str, str]]) -> list[Tuple[str, float]]:
    """Rank documents using BM25 or a bag-of-words fallback."""
    if not documents:
        return []
    if BM25Okapi is None:
        return _fallback_bm25(query, documents)
    corpus_tokens = [_tokenize(text) for _, text in documents]
    model = BM25Okapi(corpus_tokens)
    query_tokens = _tokenize(query)
    scores = model.get_scores(query_tokens)
    return [
        (doc_id, float(score))
        for (doc_id, _), score in zip(documents, scores)
    ]


def mmr(
    candidates: Sequence[Tuple[str, float, str]],
    top_k: int,
    lambda_param: float = 0.5,
    similarity: Callable[[str, str], float] | None = None,
) -> list[str]:
    """Apply maximal marginal relevance to diversify ranked candidates."""
    if not candidates:
        return []
    similarity = similarity or _default_similarity
    selected: list[Tuple[str, float, str]] = []
    remaining = list(candidates)
    while remaining and len(selected) < top_k:
        best_candidate = None
        best_score = float("-inf")
        for candidate in remaining:
            candidate_id, relevance, text = candidate
            diversity = 0.0
            if selected:
                diversity = max(similarity(text, chosen[2]) for chosen in selected)
            score = lambda_param * relevance - (1 - lambda_param) * diversity
            if score > best_score:
                best_score = score
                best_candidate = candidate
        if best_candidate is None:
            break
        selected.append(best_candidate)
        remaining.remove(best_candidate)
    return [identifier for identifier, _, _ in selected]


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in text.split() if token]


def _fallback_bm25(query: str, documents: Sequence[Tuple[str, str]]) -> list[Tuple[str, float]]:
    query_terms = set(_tokenize(query))
    scores: list[Tuple[str, float]] = []
    for doc_id, text in documents:
        terms = _tokenize(text)
        overlap = len(query_terms.intersection(terms))
        length_penalty = 1.0 / (1.0 + len(terms))
        score = overlap * length_penalty
        scores.append((doc_id, float(score)))
    scores.sort(key=lambda item: item[1], reverse=True)
    return scores


def _default_similarity(a: str, b: str) -> float:
    if fuzz is None:
        set_a = set(_tokenize(a))
        set_b = set(_tokenize(b))
        if not set_a or not set_b:
            return 0.0
        return len(set_a.intersection(set_b)) / len(set_a.union(set_b))
    return fuzz.token_set_ratio(a, b) / 100.0


__all__ = ["reciprocal_rank_fusion", "bm25_rank", "mmr", "RankedItem"]
