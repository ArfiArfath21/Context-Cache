"""Ingest pipeline orchestration."""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, Sequence
from urllib.parse import urlparse

import orjson

from context_cache.core.config import Settings
from context_cache.core.logging import get_logger
from context_cache.db.sqlite import SQLiteDatabase
from context_cache.ingest.chunker import build_chunk_payloads, chunk_text
from context_cache.ingest.dedupe import dedupe_documents
from context_cache.ingest.embeddings import EmbeddingModel
from context_cache.ingest.loaders import LoaderRegistry
from context_cache.ingest.types import IngestResult, IngestStats, LoadedDocument
from context_cache.retrieval.vector_index import VectorIndex
from context_cache.core.metrics import INDEX_SIZE
from context_cache.utils.ids import new_id
from context_cache.utils.time import now_ms

logger = get_logger(__name__)


@dataclass(slots=True)
class SourceRecord:
    id: str
    kind: str
    uri: str
    label: str | None
    include_glob: str | None
    exclude_glob: str | None


class IngestPipeline:
    """Coordinate loaders, chunking, embeddings, and persistence."""

    def __init__(
        self,
        database: SQLiteDatabase,
        settings: Settings,
        embedding_model: EmbeddingModel | None = None,
        vector_index: VectorIndex | None = None,
    ) -> None:
        self.db = database
        self.settings = settings
        self.loader_registry = LoaderRegistry()
        self.embedding_model = embedding_model or EmbeddingModel.get(settings.embedding_model)
        self.vector_index = vector_index

    def ingest_paths(self, paths: Sequence[Path]) -> dict[str, object]:
        stats = IngestStats()
        results: list[IngestResult] = []
        job_id = self._start_job(source_id=None)
        try:
            for path in paths:
                normalized = path.expanduser().resolve()
                source_id = self._ensure_source_for_path(normalized)
                outcome = self._process_path(source_id, normalized)
                results.extend(outcome)
                _update_stats_from_results(stats, outcome)
            self._finish_job(job_id, "completed", stats)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Ingest job failed: %s", exc)
            self._finish_job(job_id, "failed", stats, detail=str(exc))
            raise
        return {"job_id": job_id, "stats": stats.to_dict(), "results": [asdict(r) for r in results]}

    def ingest_sources(self, source_ids: Sequence[str] | None = None) -> dict[str, object]:
        records = self._fetch_sources(source_ids)
        stats = IngestStats()
        results: list[IngestResult] = []
        job_id = self._start_job(source_id=None if len(records) != 1 else records[0].id)
        try:
            for record in records:
                paths = list(self._list_files_for_source(record))
                logger.info("Ingesting %s files for source %s", len(paths), record.id)
                for path in paths:
                    outcome = self._process_path(record.id, path)
                    results.extend(outcome)
                    _update_stats_from_results(stats, outcome)
            self._finish_job(job_id, "completed", stats)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Ingest job failed: %s", exc)
            self._finish_job(job_id, "failed", stats, detail=str(exc))
            raise
        return {"job_id": job_id, "stats": stats.to_dict(), "results": [asdict(r) for r in results]}

    # Internal helpers -------------------------------------------------

    def _process_path(self, source_id: str, path: Path) -> list[IngestResult]:
        try:
            documents = self.loader_registry.load(path)
        except Exception as exc:
            logger.exception("Failed to load %s: %s", path, exc)
            return [IngestResult(document_id=None, path=path, status="error", detail=str(exc))]

        processed: list[IngestResult] = []
        for loaded, digest in dedupe_documents(documents):
            try:
                processed.append(self._persist_document(source_id, loaded, digest))
            except Exception as exc:  # pragma: no cover - database errors
                logger.exception("Failed to persist %s: %s", path, exc)
                processed.append(IngestResult(document_id=None, path=path, status="error", detail=str(exc)))
        return processed

    def _persist_document(self, source_id: str, document: LoadedDocument, digest: str) -> IngestResult:
        existing = self.db.execute(
            "SELECT id, is_deleted FROM documents WHERE sha256 = ?",
            [digest],
        ).fetchone()
        if existing and not existing["is_deleted"]:
            logger.debug("Skipping duplicate document %s", document.path)
            return IngestResult(document_id=existing["id"], path=document.path, status="skipped")

        document_id = new_id("doc")
        now = now_ms()
        meta_json = orjson.dumps(document.metadata).decode("utf-8")
        raw_bytes = document.raw_bytes
        size_bytes = document.size_bytes
        self.db.execute(
            """
            INSERT INTO documents (
              id, source_id, external_id, title, author, created_ts, modified_ts,
              mime, sha256, raw_bytes, text, meta_json, size_bytes, is_deleted,
              created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            [
                document_id,
                source_id,
                document.metadata.get("external_id") or os.fspath(document.path),
                document.title,
                document.author,
                document.created_ts,
                document.modified_ts,
                document.mime,
                digest,
                raw_bytes,
                document.text,
                meta_json,
                size_bytes,
                now,
                now,
            ],
        )

        chunk_dicts = chunk_text(
            document.text,
            target_tokens=200,
            max_tokens=320,
            min_tokens=80,
            overlap_tokens=40,
        )
        chunk_records = build_chunk_payloads(document_id, chunk_dicts)
        if not chunk_records:
            logger.warning("Document %s produced no chunks", document.path)
            self.db.commit()
            return IngestResult(document_id=document_id, path=document.path, status="skipped")

        self.db.executemany(
            """
            INSERT INTO chunks (id, document_id, ordinal, start_char, end_char, text, token_count, meta_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    chunk["id"],
                    chunk["document_id"],
                    chunk["ordinal"],
                    chunk["start_char"],
                    chunk["end_char"],
                    chunk["text"],
                    chunk["token_count"],
                    orjson.dumps(chunk["meta_json"]).decode("utf-8"),
                    now,
                )
                for chunk in chunk_records
            ],
        )

        embedding_batch = self.embedding_model.encode([chunk["text"] for chunk in chunk_records])
        vectors = embedding_batch.vectors
        dim = embedding_batch.dim
        self.db.executemany(
            """
            INSERT INTO embeddings (chunk_id, model, dim, vector, style, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    chunk["id"],
                    embedding_batch.model,
                    dim,
                    self.embedding_model.as_bytes(vectors[idx]),
                    "dense",
                    now,
                )
                for idx, chunk in enumerate(chunk_records)
            ],
        )

        if self.vector_index is not None:
            self.vector_index.upsert([chunk["id"] for chunk in chunk_records], vectors)

        self.db.commit()
        self._update_index_metric()
        return IngestResult(document_id=document_id, path=document.path, status="processed", chunks=chunk_records)

    def _start_job(self, source_id: str | None) -> str:
        job_id = new_id("job")
        now = now_ms()
        self.db.execute(
            "INSERT INTO ingest_jobs (id, source_id, started_at, status) VALUES (?, ?, ?, ?)",
            [job_id, source_id, now, "running"],
        )
        self.db.commit()
        return job_id

    def _finish_job(self, job_id: str, status: str, stats: IngestStats, detail: str | None = None) -> None:
        payload = {
            "detail": detail,
            "stats": stats.to_dict(),
        }
        self.db.execute(
            "UPDATE ingest_jobs SET finished_at = ?, status = ?, stats_json = ? WHERE id = ?",
            [now_ms(), status, orjson.dumps(payload).decode("utf-8"), job_id],
        )
        self.db.commit()

    def _fetch_sources(self, source_ids: Sequence[str] | None) -> list[SourceRecord]:
        if source_ids:
            placeholders = ",".join("?" for _ in source_ids)
            rows = self.db.query(
                f"SELECT id, kind, uri, label, include_glob, exclude_glob FROM sources WHERE id IN ({placeholders})",
                list(source_ids),
            )
        else:
            rows = self.db.query("SELECT id, kind, uri, label, include_glob, exclude_glob FROM sources", [])
        return [
            SourceRecord(
                id=row["id"],
                kind=row["kind"],
                uri=row["uri"],
                label=row["label"],
                include_glob=row["include_glob"],
                exclude_glob=row["exclude_glob"],
            )
            for row in rows
        ]

    def _list_files_for_source(self, source: SourceRecord) -> Iterable[Path]:
        parsed = urlparse(source.uri)
        if parsed.scheme and parsed.scheme != "file":
            raise ValueError(f"Unsupported URI scheme: {source.uri}")
        base_path = Path(parsed.path or source.uri).expanduser()
        if source.kind == "file":
            yield base_path
            return
        for file_path in base_path.rglob("*"):
            if file_path.is_file() and self._matches_patterns(file_path, source.include_glob, source.exclude_glob):
                yield file_path

    def _matches_patterns(self, path: Path, include: str | None, exclude: str | None) -> bool:
        path_str = path.as_posix()
        if exclude and any(fnmatch.fnmatch(path_str, pattern.strip()) for pattern in _expand_patterns(exclude)):
            return False
        if include:
            return any(fnmatch.fnmatch(path_str, pattern.strip()) for pattern in _expand_patterns(include))
        return True

    def _ensure_source_for_path(self, path: Path) -> str:
        uri = path.as_uri()
        row = self.db.execute("SELECT id FROM sources WHERE uri = ?", [uri]).fetchone()
        if row:
            return row["id"]
        now = now_ms()
        source_id = new_id("src")
        self.db.execute(
            """
            INSERT INTO sources (id, kind, uri, label, include_glob, exclude_glob, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                source_id,
                "file" if path.is_file() else "folder",
                uri,
                path.name,
                None,
                None,
                now,
                now,
            ],
        )
        self.db.commit()
        return source_id


    def _update_index_metric(self) -> None:
        try:
            if self.vector_index is not None:
                INDEX_SIZE.set(self.vector_index.size)
            else:
                row = self.db.execute("SELECT COUNT(*) AS count FROM chunks").fetchone()
                INDEX_SIZE.set(int(row["count"]) if row else 0)
        except Exception:  # pragma: no cover - metrics failures should not block ingest
            pass

def _expand_patterns(pattern: str) -> list[str]:
    patterns = []
    for part in pattern.split(","):
        part = part.strip()
        if not part:
            continue
        if "{" in part and "}" in part:
            prefix = part[: part.index("{")]
            suffix = part[part.index("}") + 1 :]
            options = part[part.index("{") + 1 : part.index("}")].split(",")
            for option in options:
                patterns.append(f"{prefix}{option}{suffix}")
        else:
            patterns.append(part)
    return patterns or [pattern]


def _update_stats_from_results(stats: IngestStats, results: Sequence[IngestResult]) -> None:
    for item in results:
        if item.status == "processed":
            stats.processed += 1
            stats.chunks += len(item.chunks or [])
        elif item.status == "skipped":
            stats.skipped += 1
        elif item.status == "error":
            stats.failed += 1


__all__ = ["IngestPipeline"]
