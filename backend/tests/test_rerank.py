"""Tests for the reranker fallback."""

from context_cache.retrieval import rerank as rerank_module


def test_fallback_rerank_without_rapidfuzz(monkeypatch) -> None:
    monkeypatch.setattr(rerank_module, "fuzz", None)
    monkeypatch.setattr(rerank_module, "CrossEncoder", None)
    reranker = rerank_module.Reranker("unused-model")
    candidates = [
        {"chunk_id": "a", "text": "pasta recipes for a quick dinner"},
        {"chunk_id": "b", "text": "how to reset a router password"},
    ]

    ranked = reranker.rerank("reset router password", candidates)

    assert [item["chunk_id"] for item in ranked] == ["b", "a"]
    assert all(0.0 <= item["rerank_score"] <= 1.0 for item in ranked)


def test_fallback_similarity_is_case_insensitive() -> None:
    assert rerank_module._fallback_similarity("Router", "router") == 1.0
