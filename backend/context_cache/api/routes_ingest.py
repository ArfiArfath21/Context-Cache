"""Ingest API routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends

from context_cache.api.dependencies import get_ingest_pipeline
from context_cache.ingest.pipeline import IngestPipeline
from context_cache.models.dto import IngestRequest, IngestResponse

router = APIRouter()


@router.post("", response_model=IngestResponse, summary="Trigger ingest")
async def trigger_ingest(
    request: IngestRequest,
    pipeline: IngestPipeline = Depends(get_ingest_pipeline),
) -> IngestResponse:
    if request.paths:
        paths = [Path(path).expanduser() for path in request.paths]
        payload = pipeline.ingest_paths(paths)
    else:
        source_ids = request.sources
        if request.all or not source_ids:
            source_ids = None
        payload = pipeline.ingest_sources(source_ids)
    return IngestResponse(**payload)
