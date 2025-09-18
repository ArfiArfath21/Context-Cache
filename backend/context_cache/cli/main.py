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

default_host = os.environ.get("CTXC_HOST", "http://127.0.0.1:5173")


def _request(method: str, path: str, **kwargs) -> requests.Response:
    url = f"{default_host}{path}"
    resp = requests.request(method, url, timeout=60, **kwargs)
    if not resp.ok:
        raise typer.Exit(code=1)
    return resp


@app.command()
def ingest(
    all: bool = typer.Option(False, "--all", help="Ingest all sources"),
    source: Optional[str] = typer.Option(None, "--source", help="Specific source ID to ingest"),
    path: Optional[Path] = typer.Option(None, "--path", help="Ingest an explicit filesystem path"),
) -> None:
    """Trigger ingest pipeline."""
    body: dict[str, object] = {"all": all}
    if source:
        body["sources"] = [source]
    if path:
        body["paths"] = [str(path.expanduser())]
    resp = _request("POST", "/ingest", json=body)
    typer.echo(json.dumps(resp.json(), indent=2))


@app.command()
def query(
    q: str = typer.Argument(..., help="Query text"),
    k: int = typer.Option(8, "--k", help="Number of results"),
    rerank: Optional[bool] = typer.Option(None, "--rerank/--no-rerank", help="Override reranker"),
    hybrid: Optional[bool] = typer.Option(None, "--hybrid/--no-hybrid", help="Toggle hybrid search"),
) -> None:
    """Query top-k chunks."""
    payload = {"query": q, "k": k}
    if rerank is not None:
        payload["rerank"] = rerank
    if hybrid is not None:
        payload["hybrid"] = hybrid
    resp = _request("POST", "/query", json=payload)
    typer.echo(json.dumps(resp.json(), indent=2))


@sources_app.command("list")
def list_sources() -> None:
    """List registered sources."""
    resp = _request("GET", "/sources")
    typer.echo(json.dumps(resp.json(), indent=2))


@sources_app.command("add")
def add_source(
    uri: Path = typer.Argument(..., help="Filesystem path to watch"),
    label: Optional[str] = typer.Option(None, "--label", help="Friendly name"),
    include: Optional[str] = typer.Option(None, "--include", help="Glob include pattern"),
    exclude: Optional[str] = typer.Option(None, "--exclude", help="Glob exclude pattern"),
) -> None:
    """Register a folder or file source."""
    payload = {
        "uri": str(uri.expanduser()),
        "label": label,
        "include_glob": include,
        "exclude_glob": exclude,
    }
    resp = _request("POST", "/sources", json=payload)
    typer.echo(json.dumps(resp.json(), indent=2))


if __name__ == "__main__":
    app()
