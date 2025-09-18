"""Administrative routes for Context Cache."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from context_cache.api.dependencies import get_app_settings, get_database
from context_cache.core.metrics import metrics_response
from context_cache.db.sqlite import SQLiteDatabase
from context_cache.models.dto import (
    DeleteRequest,
    DeleteResponse,
    SourceCreateRequest,
    SourceResponse,
    SourceUpdateRequest,
    UpsertTagsRequest,
    UpsertTagsResponse,
)
from context_cache.utils.ids import new_id
from context_cache.utils.time import now_ms

router = APIRouter()


@router.get("/sources", response_model=list[SourceResponse], summary="List registered sources")
async def list_sources(db: SQLiteDatabase = Depends(get_database)) -> list[SourceResponse]:
    rows = db.query(
        "SELECT id, kind, uri, label, include_glob, exclude_glob, created_at, updated_at FROM sources",
        [],
    )
    return [
        _row_to_source(row)
        for row in rows
    ]


@router.post("/sources", response_model=SourceResponse, summary="Register a new source")
async def create_source(
    request: SourceCreateRequest,
    db: SQLiteDatabase = Depends(get_database),
) -> SourceResponse:
    now = now_ms()
    source_id = new_id("src")
    uri = request.uri
    if request.kind in {"folder", "file"} and not uri.startswith("file://"):
        uri = Path(uri).expanduser().resolve().as_uri()
    db.execute(
        """
        INSERT INTO sources (id, kind, uri, label, include_glob, exclude_glob, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            source_id,
            request.kind,
            uri,
            request.label,
            request.include_glob,
            request.exclude_glob,
            now,
            now,
        ],
    )
    db.commit()
    row = db.execute(
        "SELECT id, kind, uri, label, include_glob, exclude_glob, created_at, updated_at FROM sources WHERE id = ?",
        [source_id],
    ).fetchone()
    return _row_to_source(row)


# Options call for /sources
@router.options("/sources", summary="Options for /sources")
async def options_sources():
    return

@router.patch("/sources/{source_id}", response_model=SourceResponse, summary="Update an existing source")
async def update_source(
    source_id: str,
    request: SourceUpdateRequest,
    db: SQLiteDatabase = Depends(get_database),
) -> SourceResponse:
    row = db.execute("SELECT id FROM sources WHERE id = ?", [source_id]).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Source not found")
    updates: list[str] = []
    params: list[Any] = []
    if request.label is not None:
        updates.append("label = ?")
        params.append(request.label)
    if request.include_glob is not None:
        updates.append("include_glob = ?")
        params.append(request.include_glob)
    if request.exclude_glob is not None:
        updates.append("exclude_glob = ?")
        params.append(request.exclude_glob)
    if updates:
        updates.append("updated_at = ?")
        params.append(now_ms())
        params.append(source_id)
        db.execute(f"UPDATE sources SET {', '.join(updates)} WHERE id = ?", params)
        db.commit()
    updated = db.execute(
        "SELECT id, kind, uri, label, include_glob, exclude_glob, created_at, updated_at FROM sources WHERE id = ?",
        [source_id],
    ).fetchone()
    return _row_to_source(updated)


@router.delete("/sources/{source_id}", response_model=DeleteResponse, summary="Remove a source and its documents")
async def delete_source(source_id: str, db: SQLiteDatabase = Depends(get_database)) -> DeleteResponse:
    row = db.execute("SELECT id FROM sources WHERE id = ?", [source_id]).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Source not found")
    db.execute("DELETE FROM sources WHERE id = ?", [source_id])
    db.commit()
    return DeleteResponse(status="ok", deleted=1)


@router.post("/delete", response_model=DeleteResponse, summary="Delete documents or sources")
async def delete_documents(request: DeleteRequest, db: SQLiteDatabase = Depends(get_database)) -> DeleteResponse:
    deleted = 0
    if request.document_ids:
        placeholders = ",".join("?" for _ in request.document_ids)
        if request.hard:
            cursor = db.execute(
                f"DELETE FROM documents WHERE id IN ({placeholders})",
                list(request.document_ids),
            )
        else:
            cursor = db.execute(
                f"UPDATE documents SET is_deleted = 1, updated_at = ? WHERE id IN ({placeholders})",
                [now_ms(), *request.document_ids],
            )
        deleted += cursor.rowcount
    if request.source_ids:
        placeholders = ",".join("?" for _ in request.source_ids)
        if request.hard:
            cursor = db.execute(
                f"DELETE FROM sources WHERE id IN ({placeholders})",
                list(request.source_ids),
            )
        else:
            cursor = db.execute(
                f"UPDATE documents SET is_deleted = 1, updated_at = ? WHERE source_id IN ({placeholders})",
                [now_ms(), *request.source_ids],
            )
        deleted += cursor.rowcount
    db.commit()
    return DeleteResponse(status="ok" if deleted else "noop", deleted=deleted)


@router.post("/tags/upsert", response_model=UpsertTagsResponse, summary="Assign tags to documents")
async def upsert_tags(request: UpsertTagsRequest, db: SQLiteDatabase = Depends(get_database)) -> UpsertTagsResponse:
    tag_ids: list[str] = []
    for label in request.tags:
        existing = db.execute("SELECT id FROM tags WHERE label = ?", [label]).fetchone()
        if existing:
            tag_ids.append(existing["id"])
        else:
            tag_id = new_id("tag")
            db.execute(
                "INSERT INTO tags (id, label, created_at) VALUES (?, ?, ?)",
                [tag_id, label, now_ms()],
            )
            tag_ids.append(tag_id)
    updated = 0
    for document_id in request.document_ids:
        for tag_id in tag_ids:
            cursor = db.execute(
                "INSERT OR IGNORE INTO document_tags (document_id, tag_id) VALUES (?, ?)",
                [document_id, tag_id],
            )
            updated += cursor.rowcount
    db.commit()
    return UpsertTagsResponse(updated=updated)


@router.get("/metrics", summary="Prometheus metrics")
async def get_metrics():
    return metrics_response()


def _row_to_source(row) -> SourceResponse:
    return SourceResponse(
        id=row["id"],
        kind=row["kind"],
        uri=row["uri"],
        label=row["label"],
        include_glob=row["include_glob"],
        exclude_glob=row["exclude_glob"],
        created_at=_ms_to_datetime(row["created_at"]),
        updated_at=_ms_to_datetime(row["updated_at"]),
    )


def _ms_to_datetime(value: Any) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)


__all__ = ["router"]
