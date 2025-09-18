"""SQLite management utilities."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

DEFAULT_PRAGMAS = (
    "PRAGMA journal_mode=WAL;",
    "PRAGMA synchronous=NORMAL;",
    "PRAGMA foreign_keys=ON;",
    "PRAGMA temp_store=MEMORY;",
)


class SQLiteDatabase:
    """Thin wrapper around sqlite3 providing pragmatic defaults."""

    def __init__(self, db_path: Path, read_only: bool = False) -> None:
        self.db_path = db_path.expanduser()
        self.read_only = read_only
        self._connection: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        if self._connection is None:
            if not self.read_only:
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
            if self.read_only:
                uri = f"file:{self.db_path}?mode=ro"
                self._connection = sqlite3.connect(uri, uri=True)
            else:
                self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
            for pragma in DEFAULT_PRAGMAS:
                self._connection.execute(pragma)
        return self._connection

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def __enter__(self) -> "SQLiteDatabase":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.close()

    def commit(self) -> None:
        if self._connection is not None:
            self._connection.commit()

    def rollback(self) -> None:
        if self._connection is not None:
            self._connection.rollback()

    def executescript(self, script: str) -> None:
        conn = self.connect()
        conn.executescript(script)

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> sqlite3.Cursor:
        conn = self.connect()
        return conn.execute(sql, params or [])

    def executemany(self, sql: str, seq_of_params: Iterable[Sequence[Any]]) -> sqlite3.Cursor:
        conn = self.connect()
        return conn.executemany(sql, seq_of_params)

    def query(self, sql: str, params: Sequence[Any] | None = None) -> list[sqlite3.Row]:
        cursor = self.execute(sql, params)
        return cursor.fetchall()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Cursor]:
        conn = self.connect()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def ensure_schema(self, schema_sql: str | None = None) -> None:
        if schema_sql is None:
            schema_path = Path(__file__).with_name("schema.sql")
            schema_sql = schema_path.read_text(encoding="utf-8")
        self.executescript(schema_sql)


def iter_rows(cursor: sqlite3.Cursor) -> Iterator[sqlite3.Row]:
    """Yield rows from a cursor lazily."""
    while True:
        row = cursor.fetchone()
        if row is None:
            break
        yield row


__all__ = ["SQLiteDatabase", "iter_rows"]
