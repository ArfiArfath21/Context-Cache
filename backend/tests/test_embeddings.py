"""Tests for embedding utilities."""

from context_cache.ingest.embeddings import EmbeddingModel


def test_embedding_model_placeholder() -> None:
    model = EmbeddingModel.get("dummy-model")
    vectors = model.encode(["hello", "world"]).vectors
    assert len(vectors) == 2
    assert all(len(vec) == model.dim for vec in vectors)
    assert abs(sum(value * value for value in vectors[0]) - 1.0) < 1e-6
