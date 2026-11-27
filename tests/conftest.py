from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql

from ledgerflow.api.app import create_app
from ledgerflow.config import Settings

# A disposable PostgreSQL database. Each test gets its own schema inside it.
TEST_DATABASE_ENV = "LEDGERFLOW_TEST_DATABASE_URL"


def _with_search_path(url: str, schema: str) -> str:
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query.append(("options", f"-c search_path={schema}"))
    # quote(), not the default '+' for spaces: libpq does not decode '+'.
    return urlunsplit(parts._replace(query=urlencode(query, quote_via=quote)))


@pytest.fixture
def database_url() -> Iterator[str]:
    admin_url = os.environ.get(TEST_DATABASE_ENV)
    if not admin_url:
        pytest.skip(f"set {TEST_DATABASE_ENV} to a disposable PostgreSQL database")
    schema = f"lf_test_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(admin_url, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    try:
        yield _with_search_path(admin_url, schema)
    finally:
        with psycopg.connect(admin_url, autocommit=True) as admin:
            admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


@pytest.fixture
def settings(tmp_path: Path, database_url: str) -> Settings:
    return Settings(
        app_env="test",
        public_origin="https://ledgerflow.test",
        database_url=database_url,
        object_store_root=tmp_path / "objects",
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    # Context manager runs the lifespan: opens the pool and applies migrations.
    with TestClient(create_app(settings)) as test_client:
        yield test_client
