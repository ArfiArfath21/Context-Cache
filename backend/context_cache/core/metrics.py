"""Prometheus metrics instrumentation."""

from __future__ import annotations

from fastapi import Response

try:  # pragma: no cover - optional dependency
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )
except Exception:  # pragma: no cover - fallback when prometheus unavailable
    CONTENT_TYPE_LATEST = "text/plain"

    class _NoopMetric:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def labels(self, *args, **kwargs):  # noqa: D401
            return self

        def inc(self, *args, **kwargs) -> None:  # noqa: D401
            pass

        def observe(self, *args, **kwargs) -> None:  # noqa: D401
            pass

        def set(self, *args, **kwargs) -> None:  # noqa: D401
            pass

    class _NoopRegistry:  # noqa: D401
        def __init__(self, *args, **kwargs) -> None:
            pass

    CollectorRegistry = _NoopRegistry  # type: ignore
    Counter = Gauge = Histogram = _NoopMetric  # type: ignore

    def generate_latest(_registry: object = None) -> bytes:  # noqa: D401
        return b""

REGISTRY = CollectorRegistry()

REQUEST_COUNT = Counter(
    "ctxc_requests_total",
    "Total HTTP requests",
    labelnames=("endpoint", "method", "status"),
)

REQUEST_LATENCY = Histogram(
    "ctxc_request_latency_seconds",
    "Latency of HTTP requests",
    labelnames=("endpoint", "method"),
)

INGEST_DURATION = Histogram(
    "ctxc_ingest_duration_seconds",
    "Ingest pipeline duration",
    labelnames=("source",),
)

INDEX_SIZE = Gauge(
    "ctxc_index_chunks",
    "Number of chunks stored in index",
)


def metrics_response() -> Response:
    """Return Prometheus metrics as an HTTP response."""
    payload = generate_latest(REGISTRY)
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)


__all__ = [
    "REGISTRY",
    "REQUEST_COUNT",
    "REQUEST_LATENCY",
    "INGEST_DURATION",
    "INDEX_SIZE",
    "metrics_response",
]
