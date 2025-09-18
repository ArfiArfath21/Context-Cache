"""Tests for chunker."""

from context_cache.ingest.chunker import chunk_text


def test_chunk_boundaries_basic() -> None:
    text = ("Title\n\nPara1.\n\nPara2 is longer..." * 5).strip()
    chunks = chunk_text(text, target_tokens=50, max_tokens=80, min_tokens=10)
    assert chunks, "Should produce chunks"
    ids = {chunk["id"] for chunk in chunks}
    assert len(ids) == len(chunks), "Chunk IDs should be unique"
    assert all(c["start_char"] < c["end_char"] for c in chunks)
