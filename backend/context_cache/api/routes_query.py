"""Query API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from context_cache.api.dependencies import get_query_service
from context_cache.models.dto import QueryRequest, QueryResponse, WhyResponse
from context_cache.retrieval.search import QueryService

router = APIRouter()


@router.post("/query", response_model=QueryResponse, summary="Execute a retrieval query")
async def run_query(
    request: QueryRequest,
    service: QueryService = Depends(get_query_service),
) -> QueryResponse:
    filters = request.filters.model_dump(exclude_none=True) if request.filters else None
    payload = service.query(
        query_text=request.query,
        k=request.k,
        rerank_override=request.rerank,
        hybrid=request.hybrid,
        filters=filters,
    )
    return QueryResponse(**payload)


@router.get("/why/{query_id}", response_model=WhyResponse, summary="Return stored provenance for a query")
async def explain_query(query_id: str, service: QueryService = Depends(get_query_service)) -> WhyResponse:
    payload = service.why(query_id)
    if not payload["results"]:
        raise HTTPException(status_code=404, detail="Query not found")
    return WhyResponse(**payload)
