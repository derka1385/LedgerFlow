"""PostgreSQL connection pool and numbered migrations (DATABASE.md).

Rules enforced here:
- every connection is in autocommit mode; transactions are explicit;
- a 5 s lock timeout (the P0 busy timeout) and a 30 s statement timeout;
- migrations are applied in order inside one transaction, serialised across
  processes (API and worker) with an advisory lock, and a database newer than
  this code is refused at startup.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
_MIGRATION_NAME = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")
# Arbitrary but stable key for pg_advisory_xact_lock; all runners must agree on it.
_MIGRATION_LOCK_KEY = 727_001


class SchemaTooNew(RuntimeError):
    """The database was migrated by a newer release than this code."""


def _configure(conn: psycopg.Connection) -> None:
    conn.execute("SET lock_timeout = '5s'")
    conn.execute("SET statement_timeout = '30s'")
    conn.execute("SET synchronous_commit = on")
    conn.execute("SET application_name = 'ledgerflow'")


def connect(database_url: str) -> psycopg.Connection:
    """Open one configured connection. Callers own the connection's lifetime."""
    conn = psycopg.connect(database_url, autocommit=True, row_factory=dict_row)
    _configure(conn)
    return conn


def open_pool(database_url: str, *, min_size: int = 1, max_size: int = 10) -> ConnectionPool:
    """Open a connection pool. Blocks until ``min_size`` connections are ready."""
    pool = ConnectionPool(
        database_url,
        min_size=min_size,
        max_size=max_size,
        open=True,
        timeout=10,
        kwargs={"autocommit": True, "row_factory": dict_row},
        configure=_configure,
    )
    try:
        pool.wait(timeout=10)
    except Exception:
        pool.close()
        raise
    return pool


def _known_migrations() -> list[tuple[int, Path]]:
    found: list[tuple[int, Path]] = []
    for entry in MIGRATIONS_DIR.glob("*.sql"):
        match = _MIGRATION_NAME.match(entry.name)
        if match is None:
            raise RuntimeError(f"unexpected migration file name: {entry.name}")
        found.append((int(match.group(1)), entry))
    return sorted(found)


def current_version(conn: psycopg.Connection) -> int:
    present = conn.execute("SELECT to_regclass('schema_migrations') IS NOT NULL AS present")
    if not present.fetchone()["present"]:
        return 0
    row = conn.execute("SELECT COALESCE(MAX(version), 0) AS version FROM schema_migrations")
    return int(row.fetchone()["version"])


def migrate(conn: psycopg.Connection) -> int:
    """Apply pending migrations. Returns the resulting schema version.

    All pending files run in one transaction: if any file fails, none of this
    run's changes are kept. PostgreSQL DDL is transactional, so this is safe.
    """
    migrations = _known_migrations()
    latest = migrations[-1][0] if migrations else 0
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (_MIGRATION_LOCK_KEY,))
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " version INTEGER PRIMARY KEY,"
            " applied_at TEXT NOT NULL)"
        )
        applied = current_version(conn)
        if applied > latest:
            raise SchemaTooNew(f"database schema {applied} is newer than code schema {latest}")
        for version, script in migrations:
            if version <= applied:
                continue
            # Each file inserts its own schema_migrations row.
            conn.execute(script.read_text(encoding="utf-8"))
    return current_version(conn)


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
