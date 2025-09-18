"""Text processing helpers."""

from __future__ import annotations

import re


WHITESPACE_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Collapse whitespace and strip."""
    return WHITESPACE_RE.sub(" ", text).strip()
