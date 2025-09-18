"""Time helpers."""

from __future__ import annotations

import time
from datetime import datetime, timezone


def now_ms() -> int:
    """Return current timestamp in milliseconds."""
    return int(time.time() * 1000)


def utc_now() -> datetime:
    """Return timezone-aware UTC datetime."""
    return datetime.now(tz=timezone.utc)
