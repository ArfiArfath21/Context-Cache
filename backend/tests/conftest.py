"""Test fixtures for Context Cache."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

@pytest.fixture(autouse=True)
def reset_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset global singletons and environment between tests."""
    monkeypatch.setenv("CTXC_DB_PATH", str(tmp_path / "cc.db"))
    monkeypatch.delenv("CTXC_CONFIG", raising=False)

    from context_cache.ingest.embeddings import EmbeddingModel
    from context_cache.api import dependencies as deps

    EmbeddingModel._instances.clear()
    deps.get_app_settings.cache_clear()
    deps._DB = None
    deps._VECTOR_INDEX = None
    deps._PIPELINE = None
    deps._QUERY_SERVICE = None
    yield
    EmbeddingModel._instances.clear()
    deps.get_app_settings.cache_clear()
    deps._DB = None
    deps._VECTOR_INDEX = None
    deps._PIPELINE = None
    deps._QUERY_SERVICE = None


@pytest.fixture(scope="session")
def sample_text() -> str:
    return "Title\n\nParagraph one.\n\nParagraph two is here."
