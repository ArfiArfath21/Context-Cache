"""Tests for retrieval utilities."""

from context_cache.retrieval.vector_index import VectorIndex


def test_vector_index_basic() -> None:
    index = VectorIndex(dim=3)
    index.upsert(["a", "b"], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    results = index.search([1.0, 0.0, 0.0], top_k=1)
    assert results
    assert results[0].chunk_id == "a"
