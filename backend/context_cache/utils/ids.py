"""ID helpers."""

from __future__ import annotations

import uuid


def new_id(prefix: str | None = None) -> str:
    """Generate a random UUID4 string with optional prefix."""
    base = uuid.uuid4().hex
    return f"{prefix}_{base}" if prefix else base
