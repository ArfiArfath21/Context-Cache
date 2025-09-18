"""CLI entrypoint for Context Cache."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import requests
import typer

app = typer.Typer(name="ctxc", help="Context Cache command-line interface")
sources_app = typer.Typer(name="sources")
app.add_typer(sources_app, name="sources")

DEFAULT_HOST = "http://127.0.0.1:5173"


def _resolve_host(override: Optional[str]) -> str:
    if override:
        return override.rstrip('/')
    env_host = os.environ.get("CTXC_HOST")
    if env_host:
        return env_host.rstrip('/')
    return DEFAULT_HOST


def _request(method: str, path: str, host: Optional[str] = None, **kwargs) -> requests.Response:
    base = _resolve_host(host)
    url = f"{base}{path}"
    resp = requests.request(method, url, timeout=60, **kwargs)
    if not resp.ok:
        try:
            detail = resp.json()
        except Exception:  # noqa: BLE001
            detail = resp.text
        typer.echo(f"Request failed ({resp.status_code}): {detail}", err=True)
        raise typer.Exit(code=1)
    return resp


@app.command()
def ingest(
    all: bool = typer.Option(False, "--all", help="Ingest every registered source"),
    source: Optional[str] = typer.Option(None, "--source", help="Ingest a specific source ID"),
    path: Optional[Path] = typer.Option(None, "--path", help="Ingest material at this path"),
    host: Optional[str] = typer.Option(None, "--host", help="Override backend host"),
) -> None:
    """Trigger the ingest pipeline."""
    body: dict[str, object] = {"all": all}
    if source:
        body["sources"] = [source]
    if path:
        body["paths"] = [str(path.expanduser())]
    resp = _request("POST", "/ingest", host=host, json=body)
    typer.echo(json.dumps(resp.json(), indent=2))


@app.command()
def query(
    q: str = typer.Argument(..., help="Query text"),
    k: int = typer.Option(8, "--k", help="Number of results to return"),
    rerank: Optional[bool] = typer.Option(None, "--rerank/--no-rerank", help="Force reranking on/off"),
    hybrid: Optional[bool] = typer.Option(None, "--hybrid/--no-hybrid", help="Force hybrid search on/off"),
    host: Optional[str] = typer.Option(None, "--host", help="Override backend host"),
) -> None:
    """Query the retrieval index."""
    payload: dict[str, object] = {"query": q, "k": k}
    if rerank is not None:
        payload["rerank"] = rerank
    if hybrid is not None:
        payload["hybrid"] = hybrid
    resp = _request("POST", "/query", host=host, json=payload)
    typer.echo(json.dumps(resp.json(), indent=2))


@sources_app.command("list")
def list_sources(
    host: Optional[str] = typer.Option(None, "--host", help="Override backend host"),
) -> None:
    """List registered sources."""
    resp = _request("GET", "/sources", host=host)
    typer.echo(json.dumps(resp.json(), indent=2))


@sources_app.command("add")
def add_source(
    uri: Path = typer.Argument(..., help="Filesystem path or URI"),
    label: Optional[str] = typer.Option(None, "--label", help="Friendly label"),
    include: Optional[str] = typer.Option(None, "--include", help="Include glob"),
    exclude: Optional[str] = typer.Option(None, "--exclude", help="Exclude glob"),
    host: Optional[str] = typer.Option(None, "--host", help="Override backend host"),
) -> None:
    """Register a folder/file source."""
    payload = {
        "uri": str(uri.expanduser()),
        "label": label,
        "include_glob": include,
        "exclude_glob": exclude,
    }
    resp = _request("POST", "/sources", host=host, json=payload)
    typer.echo(json.dumps(resp.json(), indent=2))


@sources_app.command("remove")
def remove_source(
    source_id: str = typer.Argument(..., help="Source identifier"),
    host: Optional[str] = typer.Option(None, "--host", help="Override backend host"),
) -> None:
    """Remove a registered source."""
    _request("DELETE", f"/sources/{source_id}", host=host)
    typer.echo(json.dumps({"status": "ok"}))


if __name__ == "__main__":
    app()
