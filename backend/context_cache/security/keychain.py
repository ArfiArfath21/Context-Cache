"""OS keychain access helpers."""

from __future__ import annotations


def store_secret(name: str, value: str) -> None:  # pragma: no cover - placeholder
    raise NotImplementedError("Keychain integration pending")


def get_secret(name: str) -> str | None:  # pragma: no cover - placeholder
    return None
