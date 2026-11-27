from __future__ import annotations

from collections.abc import Iterator

import psycopg
import pytest

from ledgerflow.persistence.db import SchemaTooNew, connect, current_version, migrate

TS = "2026-11-27T00:00:00.000Z"


@pytest.fixture
def conn(database_url: str) -> Iterator[psycopg.Connection]:
    connection = connect(database_url)
    migrate(connection)
    yield connection
    connection.close()


def _insert_tenant(conn: psycopg.Connection, tenant_id: str = "tn_1") -> None:
    conn.execute(
        "INSERT INTO tenants (id, name, created_at, daily_upload_limit, max_queued_runs)"
        " VALUES (%s, 'Demo', %s, 50, 10)",
        (tenant_id, TS),
    )


def _insert_user(conn: psycopg.Connection, user_id: str, role: str) -> None:
    conn.execute(
        "INSERT INTO users (id, tenant_id, display_name, role, created_at)"
        " VALUES (%s, 'tn_1', 'Ana', %s, %s)",
        (user_id, role, TS),
    )


def _seed_run(conn: psycopg.Connection) -> None:
    """Parent rows for one run, so FK checks stay on in the approval test."""
    _insert_tenant(conn)
    _insert_user(conn, "us_1", "accountant")
    conn.execute(
        "INSERT INTO workbooks (id, tenant_id, display_name, created_by, created_at, status)"
        " VALUES ('wb_1', 'tn_1', 'Ledger', 'us_1', %s, 'ready')",
        (TS,),
    )
    conn.execute(
        "INSERT INTO documents (id, tenant_id, workbook_id, uploaded_by, original_blob_sha256,"
        " client_upload_id, status, created_at)"
        " VALUES ('doc_1', 'tn_1', 'wb_1', 'us_1', %s, 'client-upload-1', 'uploaded', %s)",
        ("a" * 64, TS),
    )
    conn.execute(
        "INSERT INTO accounting_policies (id, tenant_id, workbook_id, revision, payload_json,"
        " sha256, confirmed_by, confirmed_at)"
        " VALUES ('pol_1', 'tn_1', 'wb_1', 1, '{}', %s, 'us_1', %s)",
        ("b" * 64, TS),
    )
    conn.execute(
        "INSERT INTO mappings (id, tenant_id, workbook_id, revision, source_sha256,"
        " layout_sha256, policy_id, payload_json, mapping_sha256, status)"
        " VALUES ('map_1', 'tn_1', 'wb_1', 1, %s, %s, 'pol_1', '{}', %s, 'confirmed')",
        ("c" * 64, "d" * 64, "e" * 64),
    )
    conn.execute(
        "INSERT INTO runs (id, tenant_id, workbook_id, document_id, created_by, state,"
        " base_version_id, base_sha256, mapping_id, policy_id, created_at, updated_at)"
        " VALUES ('run_1', 'tn_1', 'wb_1', 'doc_1', 'us_1', 'AWAITING_APPROVAL',"
        " 'ver_1', %s, 'map_1', 'pol_1', %s, %s)",
        ("f" * 64, TS, TS),
    )


def test_fresh_database_reaches_schema_version_1(conn: psycopg.Connection) -> None:
    assert current_version(conn) == 1


def test_migrate_is_idempotent(conn: psycopg.Connection) -> None:
    assert migrate(conn) == 1
    rows = conn.execute("SELECT COUNT(*) AS n FROM schema_migrations").fetchone()
    assert rows is not None and rows["n"] == 1


def test_database_newer_than_code_is_refused(conn: psycopg.Connection) -> None:
    conn.execute(
        "INSERT INTO schema_migrations (version, applied_at) VALUES (99, '2030-01-01T00:00:00Z')"
    )
    with pytest.raises(SchemaTooNew):
        migrate(conn)


def test_foreign_keys_are_enforced(conn: psycopg.Connection) -> None:
    with pytest.raises(psycopg.IntegrityError):
        conn.execute(
            "INSERT INTO users (id, tenant_id, display_name, role, created_at)"
            " VALUES ('us_1', 'missing', 'Ana', 'employee', %s)",
            (TS,),
        )


def test_role_check_rejects_unknown_role(conn: psycopg.Connection) -> None:
    _insert_tenant(conn)
    with pytest.raises(psycopg.IntegrityError):
        _insert_user(conn, "us_1", "superuser")


def test_events_are_append_only(conn: psycopg.Connection) -> None:
    _insert_tenant(conn)
    conn.execute(
        "INSERT INTO events (event_id, tenant_id, event_type, payload_json, created_at)"
        " VALUES ('ev_1', 'tn_1', 'run.created', '{}', %s)",
        (TS,),
    )
    with pytest.raises(psycopg.IntegrityError, match="append-only"):
        conn.execute("UPDATE events SET event_type = 'x' WHERE event_id = 'ev_1'")
    with pytest.raises(psycopg.IntegrityError, match="append-only"):
        conn.execute("DELETE FROM events WHERE event_id = 'ev_1'")


def test_event_sequence_is_assigned_in_insert_order(conn: psycopg.Connection) -> None:
    _insert_tenant(conn)
    for index in range(2):
        conn.execute(
            "INSERT INTO events (event_id, tenant_id, event_type, payload_json, created_at)"
            " VALUES (%s, 'tn_1', 'run.created', '{}', %s)",
            (f"ev_{index}", TS),
        )
    rows = conn.execute("SELECT event_id, sequence FROM events ORDER BY sequence").fetchall()
    assert [(r["event_id"], r["sequence"]) for r in rows] == [("ev_0", 1), ("ev_1", 2)]


def test_only_one_live_job_per_target(conn: psycopg.Connection) -> None:
    _insert_tenant(conn)
    insert = (
        "INSERT INTO jobs (id, tenant_id, kind, target_id, state, available_at,"
        " payload_json, created_at) VALUES (%s, 'tn_1', 'inspect', 'wb_1', %s, %s, '{}', %s)"
    )
    conn.execute(insert, ("job_1", "queued", TS, TS))
    with pytest.raises(psycopg.IntegrityError):
        conn.execute(insert, ("job_2", "leased", TS, TS))
    # A finished job no longer blocks a new one for the same target.
    conn.execute("UPDATE jobs SET state = 'done' WHERE id = 'job_1'")
    conn.execute(insert, ("job_3", "queued", TS, TS))


def test_only_one_accepted_approval_per_run(conn: psycopg.Connection) -> None:
    _seed_run(conn)
    approval = (
        "INSERT INTO approvals (id, tenant_id, run_id, actor_id, decision, base_version_id,"
        " base_sha256, candidate_sha256, plan_sha256, mapping_sha256,"
        " validation_report_sha256, policy_version, tuple_sha256, created_at, expires_at)"
        " VALUES (%s, 'tn_1', 'run_1', 'us_1', %s, 'ver_1', 'a', 'b', 'c', 'd', 'e', 'p1',"
        " 'f', %s, '2026-11-27T00:15:00.000Z')"
    )
    conn.execute(approval, ("ap_1", "approve", TS))
    with pytest.raises(psycopg.IntegrityError):
        conn.execute(approval, ("ap_2", "approve", TS))
    # Rejections are not limited.
    conn.execute(approval, ("ap_3", "reject", TS))


def test_workbook_and_first_version_can_be_inserted_in_one_transaction(
    conn: psycopg.Connection,
) -> None:
    # The deferred cycle foreign keys allow this; an immediate check would fail.
    _insert_tenant(conn)
    _insert_user(conn, "us_1", "owner")
    with conn.transaction():
        conn.execute(
            "INSERT INTO workbooks (id, tenant_id, display_name, created_by, created_at,"
            " current_version_id, status) VALUES ('wb_1', 'tn_1', 'Ledger', 'us_1', %s,"
            " 'ver_1', 'ready')",
            (TS,),
        )
        conn.execute(
            "INSERT INTO workbook_versions (id, tenant_id, workbook_id, sequence, blob_sha256,"
            " source, created_by, created_at)"
            " VALUES ('ver_1', 'tn_1', 'wb_1', 1, %s, 'upload', 'us_1', %s)",
            ("a" * 64, TS),
        )
