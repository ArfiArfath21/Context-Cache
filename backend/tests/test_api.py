"""API integration tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from context_cache.app import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_ingest_and_query_flow(tmp_path: Path, client: TestClient) -> None:
    sample = tmp_path / "sample.md"
    sample.write_text("# Sample\n\nThis is a sample document about retrieval.")

    ingest_resp = client.post("/ingest", json={"paths": [str(sample)]})
    assert ingest_resp.status_code == 200
    ingest_data = ingest_resp.json()
    assert ingest_data["stats"]["processed"] >= 1

    query_resp = client.post("/query", json={"query": "retrieval", "k": 4})
    assert query_resp.status_code == 200
    query_payload = query_resp.json()
    assert query_payload["results"], "Expected at least one result"

    why_resp = client.get(f"/why/{query_payload['query_id']}")
    assert why_resp.status_code == 200
    assert why_resp.json()["results"]

    sources_resp = client.get("/sources")
    assert sources_resp.status_code == 200
    assert sources_resp.json()
