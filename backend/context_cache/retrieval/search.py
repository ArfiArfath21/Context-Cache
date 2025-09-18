"""Search orchestration."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Sequence

import orjson

from context_cache.core.config import Settings
from context_cache.core.metrics import REQUEST_COUNT, REQUEST_LATENCY
from context_cache.db.sqlite import SQLiteDatabase
from context_cache.ingest.embeddings import EmbeddingModel
from context_cache.retrieval.hybrid import bm25_rank, mmr, reciprocal_rank_fusion
from context_cache.retrieval.rerank import Reranker, should_rerank
from context_cache.retrieval.vector_index import SearchResult, VectorIndex
from context_cache.utils.ids import new_id
from context_cache.utils.time import now_ms


@dataclass(slots=True)
class Candidate:
    chunk_id: str
    document_id: str
    source_id: str
    external_id: str
    text: str
    start_char: int
    end_char: int
    meta: dict[str, Any]
    dense_score: float
    bm25_score: float = 0.0
    fused_score: float = 0.0


class QueryService:
    """Coordinates dense, sparse, and rerank retrieval flows."""

    def __init__(
        self,
        db: SQLiteDatabase,
        settings: Settings,
        vector_index: VectorIndex,
        embedding_model: EmbeddingModel,
        reranker: Reranker | None = None,
    ) -> None:
        self.db = db
        self.settings = settings
        self.vector_index = vector_index
        self.embedding_model = embedding_model
        self.reranker = reranker or Reranker(settings.rerank_model)

    def query(
        self,
        query_text: str,
        k: int | None = None,
        rerank_override: bool | None = None,
        hybrid: bool | None = None,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        start_time = time.perf_counter()
        request_labels = {"endpoint": "query", "method": "POST"}
        top_k = k or self.settings.top_k_final
        dense_vector = self.embedding_model.encode([query_text]).vectors[0]
        dense_hits = self.vector_index.search(dense_vector, top_k=self.settings.top_k_dense)
        candidates = self._hydrate_candidates(dense_hits)
        candidates = self._apply_filters(candidates, filters)

        hybrid_enabled = hybrid if hybrid is not None else True
        fused_scores = self._combine_scores(query_text, dense_hits, candidates, hybrid_enabled)
        ordered_ids = [identifier for identifier, _ in fused_scores]

        if self.settings.mmr_lambda > 0 and ordered_ids:
            mmr_ids = mmr(
                [
                    (candidate.chunk_id, candidate.fused_score or candidate.dense_score, candidate.text)
                    for candidate in candidates
                    if candidate.chunk_id in ordered_ids
                ],
                top_k=max(top_k, len(ordered_ids)),
                lambda_param=self.settings.mmr_lambda,
            )
            if mmr_ids:
                ordered_ids = mmr_ids

        candidate_map = {candidate.chunk_id: candidate for candidate in candidates}
        ordered_candidates = [candidate_map[cid] for cid in ordered_ids if cid in candidate_map]

        should_run_rerank = should_rerank(self.settings.rerank_enabled, rerank_override)
        if should_run_rerank and ordered_candidates:
            rerank_input = [
                {
                    "chunk_id": candidate.chunk_id,
                    "text": candidate.text,
                    "document_id": candidate.document_id,
                    "score": candidate.fused_score or candidate.dense_score,
                }
                for candidate in ordered_candidates[: max(top_k * 2, top_k + 2)]
            ]
            reranked = self.reranker.rerank(query_text, rerank_input, top_k=len(rerank_input))
            ordered_candidates = [candidate_map[item["chunk_id"]] for item in reranked if item["chunk_id"] in candidate_map]

        final_candidates = ordered_candidates[:top_k]
        query_id = self._persist_query(query_text, filters, should_run_rerank, final_candidates)
        results = [self._build_result(candidate, idx, query_id) for idx, candidate in enumerate(final_candidates)]

        duration = time.perf_counter() - start_time
        REQUEST_LATENCY.labels(**request_labels).observe(duration)
        REQUEST_COUNT.labels(endpoint="query", method="POST", status="200").inc()
        return {"query_id": query_id, "results": results}

    def why(self, query_id: str, limit: int | None = None) -> dict[str, Any]:
        params: list[Any] = [query_id]
        limit_clause = ""
        if limit is not None:
            limit_clause = " LIMIT ?"
            params.append(limit)
        rows = self.db.query(
            f"""
            SELECT
              qr.chunk_id,
              qr.rank,
              qr.score,
              qr.provenance_json,
              chunks.text,
              chunks.start_char,
              chunks.end_char,
              chunks.document_id
            FROM query_results qr
            JOIN chunks ON chunks.id = qr.chunk_id
            WHERE qr.query_id = ?{limit_clause}
            ORDER BY qr.rank ASC
            """,
            params,
        )
        results: list[dict[str, Any]] = []
        for row in rows:
            provenance = orjson.loads(row["provenance_json"]) if row["provenance_json"] else {}
            results.append(
                {
                    "chunk_id": row["chunk_id"],
                    "document_id": row["document_id"],
                    "score": float(row["score"]),
                    "text": row["text"],
                    "start_char": row["start_char"],
                    "end_char": row["end_char"],
                    "provenance": provenance,
                }
            )
        return {"query_id": query_id, "results": results}

    # ------------------------------------------------------------------

    def _hydrate_candidates(self, dense_hits: Sequence[SearchResult]) -> list[Candidate]:
        if not dense_hits:
            return []
        ids = [hit.chunk_id for hit in dense_hits]
        placeholders = ",".join("?" for _ in ids)
        rows = self.db.query(
            f"""
            SELECT
              chunks.id AS chunk_id,
              chunks.document_id,
              chunks.text,
              chunks.start_char,
              chunks.end_char,
              chunks.meta_json,
              documents.source_id,
              documents.external_id,
              documents.meta_json AS document_meta,
              sources.uri
            FROM chunks
            JOIN documents ON documents.id = chunks.document_id
            JOIN sources ON sources.id = documents.source_id
            WHERE chunks.id IN ({placeholders})
            """,
            ids,
        )
        row_map = {row["chunk_id"]: row for row in rows}
        candidates: list[Candidate] = []
        for hit in dense_hits:
            row = row_map.get(hit.chunk_id)
            if not row:
                continue
            meta = {}
            if row["meta_json"]:
                meta.update(orjson.loads(row["meta_json"]))
            if row["document_meta"]:
                meta.setdefault("document", orjson.loads(row["document_meta"]))
            meta["uri"] = row["uri"]
            candidates.append(
                Candidate(
                    chunk_id=hit.chunk_id,
                    document_id=row["document_id"],
                    source_id=row["source_id"],
                    external_id=row["external_id"],
                    text=row["text"],
                    start_char=row["start_char"],
                    end_char=row["end_char"],
                    meta=meta,
                    dense_score=hit.score,
                )
            )
        return candidates

    def _apply_filters(self, candidates: list[Candidate], filters: dict[str, Any] | None) -> list[Candidate]:
        if not filters:
            return candidates
        filtered = candidates
        source_ids = filters.get("source_ids")
        if source_ids:
            filtered = [item for item in filtered if item.source_id in source_ids]
        document_ids = filters.get("document_ids")
        if document_ids:
            filtered = [item for item in filtered if item.document_id in document_ids]
        tags = filters.get("tags")
        if tags and filtered:
            tag_placeholders = ",".join("?" for _ in tags)
            doc_ids = [item.document_id for item in filtered]
            doc_placeholders = ",".join("?" for _ in doc_ids)
            if doc_ids:
                rows = self.db.query(
                    f"""
                    SELECT document_id, COUNT(DISTINCT tags.label) AS tag_count
                    FROM document_tags
                    JOIN tags ON tags.id = document_tags.tag_id
                    WHERE tags.label IN ({tag_placeholders}) AND document_id IN ({doc_placeholders})
                    GROUP BY document_id
                    """,
                    [*tags, *doc_ids],
                )
                allowed = {row["document_id"] for row in rows if row["tag_count"] >= len(tags)}
                filtered = [item for item in filtered if item.document_id in allowed]
        return filtered

    def _combine_scores(
        self,
        query_text: str,
        dense_hits: Sequence[SearchResult],
        candidates: Sequence[Candidate],
        hybrid: bool,
    ) -> list[tuple[str, float]]:
        dense_pairs = [(hit.chunk_id, hit.score) for hit in dense_hits]
        if not hybrid or not candidates:
            score_map = {chunk_id: score for chunk_id, score in dense_pairs}
            for candidate in candidates:
                candidate.fused_score = score_map.get(candidate.chunk_id, candidate.dense_score)
            return sorted(score_map.items(), key=lambda item: item[1], reverse=True)

        bm25_pairs = bm25_rank(query_text, [(candidate.chunk_id, candidate.text) for candidate in candidates])
        for candidate in candidates:
            candidate.bm25_score = next((score for cid, score in bm25_pairs if cid == candidate.chunk_id), 0.0)
        fused = reciprocal_rank_fusion([dense_pairs, bm25_pairs])
        score_map = {item.identifier: item.score for item in fused}
        for candidate in candidates:
            candidate.fused_score = score_map.get(candidate.chunk_id, candidate.dense_score)
        return [(identifier, score_map.get(identifier, 0.0)) for identifier in score_map]

    def _persist_query(
        self,
        query_text: str,
        filters: dict[str, Any] | None,
        rerank_ran: bool,
        candidates: Sequence[Candidate],
    ) -> str:
        query_id = new_id("qry")
        self.db.execute(
            "INSERT INTO queries (id, query, filters_json, rerank_enabled, created_at) VALUES (?, ?, ?, ?, ?)",
            [
                query_id,
                query_text,
                orjson.dumps(filters or {}).decode("utf-8"),
                int(rerank_ran),
                now_ms(),
            ],
        )
        self.db.executemany(
            """
            INSERT INTO query_results (id, query_id, chunk_id, rank, score, provenance_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    new_id("res"),
                    query_id,
                    candidate.chunk_id,
                    idx,
                    float(candidate.fused_score or candidate.dense_score),
                    orjson.dumps(candidate.meta).decode("utf-8"),
                    now_ms(),
                )
                for idx, candidate in enumerate(candidates)
            ],
        )
        self.db.commit()
        return query_id

    def _build_result(self, candidate: Candidate, rank: int, query_id: str) -> dict[str, Any]:
        base_score = candidate.fused_score or candidate.dense_score
        deep_link = f"{candidate.external_id}#char={candidate.start_char}-{candidate.end_char}"
        provenance = {
            "query_id": query_id,
            "rank": rank,
            "score": base_score,
            "source_id": candidate.source_id,
            "document_id": candidate.document_id,
            "external_id": candidate.external_id,
            "uri": candidate.meta.get("uri"),
            "meta": candidate.meta,
            "deep_link": deep_link,
        }
        return {
            "chunk_id": candidate.chunk_id,
            "document_id": candidate.document_id,
            "score": base_score,
            "text": candidate.text,
            "start_char": candidate.start_char,
            "end_char": candidate.end_char,
            "provenance": provenance,
        }


__all__ = ["QueryService"]
