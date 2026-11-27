-- LedgerFlow schema 0001 (PostgreSQL). Normative source: docs/DATABASE.md.
-- The runner applies this file inside one transaction together with its
-- schema_migrations bookkeeping. Do not add BEGIN/COMMIT here.
--
-- Conventions from DATABASE.md: identifiers and timestamps are TEXT (UTC),
-- booleans are INTEGER 0/1, money and revisions are INTEGER.

-- Shared helper for append-only and immutable tables. The message is the
-- trigger argument; SQLSTATE 23514 (check_violation) maps to IntegrityError.
CREATE FUNCTION reject_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION '%', TG_ARGV[0] USING ERRCODE = 'check_violation';
END;
$$;

-- Tenancy and identity ------------------------------------------------------

CREATE TABLE tenants (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    created_at          TEXT NOT NULL,
    daily_upload_limit  INTEGER NOT NULL CHECK (daily_upload_limit >= 0),
    max_queued_runs     INTEGER NOT NULL CHECK (max_queued_runs >= 0)
);

CREATE TABLE users (
    id            TEXT PRIMARY KEY,
    tenant_id     TEXT NOT NULL REFERENCES tenants(id),
    display_name  TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('employee', 'accountant', 'owner')),
    active        INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at    TEXT NOT NULL,
    UNIQUE (tenant_id, id)
);

CREATE TABLE invites (
    id           TEXT PRIMARY KEY,
    tenant_id    TEXT NOT NULL,
    user_id      TEXT NOT NULL,
    token_hash   TEXT NOT NULL UNIQUE,
    expires_at   TEXT NOT NULL,
    consumed_at  TEXT,
    created_at   TEXT NOT NULL,
    FOREIGN KEY (tenant_id, user_id) REFERENCES users (tenant_id, id)
);

CREATE TABLE sessions (
    id                 TEXT PRIMARY KEY,
    tenant_id          TEXT NOT NULL,
    user_id            TEXT NOT NULL,
    token_hash         TEXT NOT NULL UNIQUE,
    csrf_token_hash    TEXT NOT NULL,
    created_at         TEXT NOT NULL,
    expires_at         TEXT NOT NULL,
    revoked_at         TEXT,
    FOREIGN KEY (tenant_id, user_id) REFERENCES users (tenant_id, id)
);
CREATE INDEX sessions_expires_at ON sessions (expires_at);

-- Content-addressed storage metadata (bytes live outside the database) -------

CREATE TABLE blobs (
    tenant_id          TEXT NOT NULL REFERENCES tenants (id),
    sha256             TEXT NOT NULL CHECK (length(sha256) = 64),
    kind               TEXT NOT NULL,
    byte_length        INTEGER NOT NULL CHECK (byte_length > 0),
    storage_object_id  TEXT NOT NULL,
    created_at         TEXT NOT NULL,
    deleted_at         TEXT,
    PRIMARY KEY (tenant_id, sha256, kind)
);

-- Workbooks, versions and mappings -------------------------------------------
-- Two foreign keys close cycles (workbooks <-> workbook_versions and
-- workbook_versions <-> commits). They are added at the end of this file,
-- once both tables exist, as DEFERRABLE INITIALLY DEFERRED.

CREATE TABLE workbooks (
    id                  TEXT PRIMARY KEY,
    tenant_id           TEXT NOT NULL REFERENCES tenants (id),
    display_name        TEXT NOT NULL,
    created_by          TEXT NOT NULL,
    created_at          TEXT NOT NULL,
    current_version_id  TEXT,
    active_mapping_id   TEXT,
    revision            INTEGER NOT NULL DEFAULT 0 CHECK (revision >= 0),
    status              TEXT NOT NULL,
    UNIQUE (tenant_id, id),
    FOREIGN KEY (tenant_id, created_by) REFERENCES users (tenant_id, id)
);

CREATE TABLE workbook_versions (
    id                  TEXT PRIMARY KEY,
    tenant_id           TEXT NOT NULL,
    workbook_id         TEXT NOT NULL,
    sequence            INTEGER NOT NULL CHECK (sequence >= 1),
    parent_version_id   TEXT,
    blob_sha256         TEXT NOT NULL,
    source              TEXT NOT NULL CHECK (source IN ('upload', 'agent_commit')),
    commit_id           TEXT,
    created_by          TEXT NOT NULL,
    created_at          TEXT NOT NULL,
    UNIQUE (workbook_id, sequence),
    UNIQUE (tenant_id, id),
    FOREIGN KEY (tenant_id, workbook_id) REFERENCES workbooks (tenant_id, id),
    FOREIGN KEY (tenant_id, parent_version_id) REFERENCES workbook_versions (tenant_id, id)
);
CREATE INDEX workbook_versions_sequence_desc ON workbook_versions (workbook_id, sequence DESC);

CREATE TABLE upload_assignments (
    tenant_id    TEXT NOT NULL,
    user_id      TEXT NOT NULL,
    workbook_id  TEXT NOT NULL,
    can_upload   INTEGER NOT NULL DEFAULT 1 CHECK (can_upload IN (0, 1)),
    created_at   TEXT NOT NULL,
    PRIMARY KEY (tenant_id, user_id, workbook_id),
    FOREIGN KEY (tenant_id, user_id) REFERENCES users (tenant_id, id),
    FOREIGN KEY (tenant_id, workbook_id) REFERENCES workbooks (tenant_id, id)
);

CREATE TABLE inspections (
    id                      TEXT PRIMARY KEY,
    tenant_id               TEXT NOT NULL,
    workbook_id             TEXT NOT NULL,
    version_id              TEXT NOT NULL,
    inspector_version       TEXT NOT NULL,
    manifest_sha256         TEXT NOT NULL,
    baseline_report_sha256  TEXT,
    status                  TEXT NOT NULL,
    payload_json            TEXT NOT NULL,
    created_at              TEXT NOT NULL,
    UNIQUE (version_id, inspector_version),
    FOREIGN KEY (tenant_id, workbook_id) REFERENCES workbooks (tenant_id, id),
    FOREIGN KEY (tenant_id, version_id) REFERENCES workbook_versions (tenant_id, id)
);

CREATE TABLE accounting_policies (
    id            TEXT PRIMARY KEY,
    tenant_id     TEXT NOT NULL,
    workbook_id   TEXT NOT NULL,
    revision      INTEGER NOT NULL CHECK (revision >= 1),
    payload_json  TEXT NOT NULL,
    sha256        TEXT NOT NULL,
    confirmed_by  TEXT NOT NULL,
    confirmed_at  TEXT NOT NULL,
    UNIQUE (workbook_id, revision),
    FOREIGN KEY (tenant_id, workbook_id) REFERENCES workbooks (tenant_id, id)
);

CREATE TABLE mappings (
    id              TEXT PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    workbook_id     TEXT NOT NULL,
    revision        INTEGER NOT NULL CHECK (revision >= 1),
    source_sha256   TEXT NOT NULL,
    layout_sha256   TEXT NOT NULL,
    policy_id       TEXT REFERENCES accounting_policies (id),
    payload_json    TEXT NOT NULL,
    mapping_sha256  TEXT NOT NULL,
    status          TEXT NOT NULL,
    confirmed_by    TEXT,
    confirmed_at    TEXT,
    UNIQUE (workbook_id, revision),
    FOREIGN KEY (tenant_id, workbook_id) REFERENCES workbooks (tenant_id, id)
);

-- Receipts, transactions and duplicate handling ------------------------------

CREATE TABLE documents (
    id                        TEXT PRIMARY KEY,
    tenant_id                 TEXT NOT NULL,
    workbook_id               TEXT NOT NULL,
    uploaded_by               TEXT NOT NULL,
    original_blob_sha256      TEXT NOT NULL,
    normalized_blob_sha256    TEXT,
    client_upload_id          TEXT NOT NULL,
    status                    TEXT NOT NULL,
    created_at                TEXT NOT NULL,
    UNIQUE (tenant_id, uploaded_by, client_upload_id),
    UNIQUE (tenant_id, id),
    FOREIGN KEY (tenant_id, workbook_id) REFERENCES workbooks (tenant_id, id),
    FOREIGN KEY (tenant_id, uploaded_by) REFERENCES users (tenant_id, id)
);
CREATE INDEX documents_original_hash ON documents (tenant_id, original_blob_sha256);

CREATE TABLE transactions (
    id                        TEXT NOT NULL,
    tenant_id                 TEXT NOT NULL,
    workbook_id               TEXT NOT NULL,
    document_id               TEXT NOT NULL,
    revision                  INTEGER NOT NULL CHECK (revision >= 1),
    payload_json              TEXT NOT NULL,
    payload_sha256            TEXT NOT NULL,
    exact_duplicate_key       TEXT NOT NULL,
    semantic_duplicate_key    TEXT,
    review_status             TEXT NOT NULL,
    created_at                TEXT NOT NULL,
    PRIMARY KEY (id, revision),
    UNIQUE (tenant_id, id, revision),
    FOREIGN KEY (tenant_id, workbook_id) REFERENCES workbooks (tenant_id, id),
    FOREIGN KEY (tenant_id, document_id) REFERENCES documents (tenant_id, id)
);
CREATE INDEX transactions_semantic_key
    ON transactions (tenant_id, workbook_id, semantic_duplicate_key);

CREATE TABLE duplicate_resolutions (
    id                       TEXT PRIMARY KEY,
    tenant_id                TEXT NOT NULL,
    transaction_id           TEXT NOT NULL,
    transaction_revision     INTEGER NOT NULL,
    related_transaction_id   TEXT NOT NULL,
    decision                 TEXT NOT NULL,
    reason                   TEXT NOT NULL,
    actor_id                 TEXT NOT NULL,
    created_at               TEXT NOT NULL,
    FOREIGN KEY (tenant_id, transaction_id, transaction_revision)
        REFERENCES transactions (tenant_id, id, revision),
    FOREIGN KEY (tenant_id, actor_id) REFERENCES users (tenant_id, id)
);

-- Runs, jobs and leases -------------------------------------------------------

CREATE TABLE runs (
    id                        TEXT PRIMARY KEY,
    tenant_id                 TEXT NOT NULL,
    workbook_id               TEXT NOT NULL,
    document_id               TEXT NOT NULL,
    transaction_id            TEXT,
    transaction_revision      INTEGER,
    created_by                TEXT NOT NULL,
    state                     TEXT NOT NULL,
    state_reason              TEXT,
    revision                  INTEGER NOT NULL DEFAULT 0 CHECK (revision >= 0),
    base_version_id           TEXT NOT NULL,
    base_sha256               TEXT NOT NULL,
    mapping_id                TEXT NOT NULL,
    policy_id                 TEXT NOT NULL,
    plan_id                   TEXT,
    attempt_count             INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    model_request_count       INTEGER NOT NULL DEFAULT 0 CHECK (model_request_count >= 0),
    active_elapsed_ms         INTEGER NOT NULL DEFAULT 0 CHECK (active_elapsed_ms >= 0),
    cancel_requested          INTEGER NOT NULL DEFAULT 0 CHECK (cancel_requested IN (0, 1)),
    created_at                TEXT NOT NULL,
    updated_at                TEXT NOT NULL,
    review_expires_at         TEXT,
    approval_expires_at       TEXT,
    UNIQUE (tenant_id, id),
    FOREIGN KEY (tenant_id, workbook_id) REFERENCES workbooks (tenant_id, id),
    FOREIGN KEY (tenant_id, document_id) REFERENCES documents (tenant_id, id),
    FOREIGN KEY (tenant_id, created_by) REFERENCES users (tenant_id, id),
    FOREIGN KEY (tenant_id, transaction_id, transaction_revision)
        REFERENCES transactions (tenant_id, id, revision),
    FOREIGN KEY (mapping_id) REFERENCES mappings (id),
    FOREIGN KEY (policy_id) REFERENCES accounting_policies (id)
);
CREATE INDEX runs_tenant_created ON runs (tenant_id, created_at, id);
CREATE INDEX runs_workbook_state ON runs (workbook_id, state);

CREATE TABLE jobs (
    id               TEXT PRIMARY KEY,
    tenant_id        TEXT NOT NULL,
    kind             TEXT NOT NULL CHECK (kind IN ('inspect', 'normalize', 'map', 'run')),
    run_id           TEXT,
    target_id        TEXT NOT NULL,
    state            TEXT NOT NULL CHECK (state IN ('queued', 'leased', 'done', 'failed', 'cancelled')),
    available_at     TEXT NOT NULL,
    lease_owner      TEXT,
    lease_expires_at TEXT,
    epoch            INTEGER NOT NULL DEFAULT 0 CHECK (epoch >= 0),
    revision         INTEGER NOT NULL DEFAULT 0 CHECK (revision >= 0),
    payload_json     TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, id)
);
CREATE INDEX jobs_claimable ON jobs (state, available_at, lease_expires_at);
-- At most one live job per target: a queued or leased job blocks a second one.
CREATE UNIQUE INDEX jobs_one_live_per_target
    ON jobs (kind, target_id) WHERE state IN ('queued', 'leased');

CREATE TABLE workbook_execution_locks (
    workbook_id      TEXT PRIMARY KEY,
    tenant_id        TEXT NOT NULL,
    run_id           TEXT NOT NULL,
    job_id           TEXT NOT NULL,
    epoch            INTEGER NOT NULL CHECK (epoch >= 0),
    lease_expires_at TEXT NOT NULL,
    FOREIGN KEY (tenant_id, workbook_id) REFERENCES workbooks (tenant_id, id),
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, id),
    FOREIGN KEY (job_id) REFERENCES jobs (id)
);

CREATE TABLE plans (
    id                    TEXT PRIMARY KEY,
    tenant_id             TEXT NOT NULL,
    run_id                TEXT NOT NULL,
    revision              INTEGER NOT NULL CHECK (revision >= 1),
    payload_json          TEXT NOT NULL,
    plan_sha256           TEXT NOT NULL,
    mapping_sha256        TEXT NOT NULL,
    transaction_revision  INTEGER NOT NULL,
    created_at            TEXT NOT NULL,
    UNIQUE (run_id, revision),
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, id)
);

CREATE TABLE attempts (
    id                     TEXT PRIMARY KEY,
    tenant_id              TEXT NOT NULL,
    run_id                 TEXT NOT NULL,
    number                 INTEGER NOT NULL CHECK (number >= 1),
    job_epoch              INTEGER NOT NULL,
    code_blob_sha256       TEXT,
    plan_sha256            TEXT,
    image_digest           TEXT,
    runtime                TEXT,
    runtime_policy_version TEXT NOT NULL,
    supervisor_job_id      TEXT NOT NULL UNIQUE,
    state                  TEXT NOT NULL,
    exit_code              INTEGER,
    termination_reason     TEXT,
    started_at             TEXT,
    finished_at            TEXT,
    duration_ms            INTEGER,
    peak_memory_bytes      INTEGER,
    cleanup_status         TEXT NOT NULL,
    cleanup_at             TEXT,
    UNIQUE (run_id, number),
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, id)
);

-- Artifacts, validation and approval ------------------------------------------

CREATE TABLE artifacts (
    id             TEXT PRIMARY KEY,
    tenant_id      TEXT NOT NULL,
    run_id         TEXT NOT NULL,
    attempt_id     TEXT REFERENCES attempts (id),
    kind           TEXT NOT NULL CHECK (kind IN ('candidate', 'code', 'log', 'report', 'diff', 'evidence')),
    blob_sha256    TEXT NOT NULL,
    byte_length    INTEGER NOT NULL CHECK (byte_length >= 0),
    frozen_at      TEXT,
    created_at     TEXT NOT NULL,
    expires_at     TEXT,
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, id)
);
CREATE INDEX artifacts_run_kind ON artifacts (run_id, kind);

CREATE TABLE validation_reports (
    id                         TEXT PRIMARY KEY,
    tenant_id                  TEXT NOT NULL,
    run_id                     TEXT NOT NULL,
    attempt_id                 TEXT NOT NULL REFERENCES attempts (id),
    candidate_sha256           TEXT NOT NULL,
    base_sha256                TEXT NOT NULL,
    plan_sha256                TEXT NOT NULL,
    mapping_sha256             TEXT NOT NULL,
    verifier_version           TEXT NOT NULL,
    payload_json               TEXT NOT NULL,
    report_sha256              TEXT NOT NULL,
    host_attestation_sha256    TEXT,
    result                     TEXT NOT NULL CHECK (result IN ('pass', 'fail', 'review')),
    created_at                 TEXT NOT NULL,
    UNIQUE (attempt_id, candidate_sha256, verifier_version),
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, id)
);

CREATE TABLE approvals (
    id                          TEXT PRIMARY KEY,
    tenant_id                   TEXT NOT NULL,
    run_id                      TEXT NOT NULL,
    actor_id                    TEXT NOT NULL,
    decision                    TEXT NOT NULL CHECK (decision IN ('approve', 'reject')),
    base_version_id             TEXT NOT NULL,
    base_sha256                 TEXT NOT NULL,
    candidate_sha256            TEXT NOT NULL,
    plan_sha256                 TEXT NOT NULL,
    mapping_sha256              TEXT NOT NULL,
    validation_report_sha256    TEXT NOT NULL,
    policy_version              TEXT NOT NULL,
    tuple_sha256                TEXT NOT NULL,
    comment                     TEXT,
    created_at                  TEXT NOT NULL,
    expires_at                  TEXT NOT NULL,
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, id),
    FOREIGN KEY (tenant_id, actor_id) REFERENCES users (tenant_id, id)
);
-- At most one accepted approval per run.
CREATE UNIQUE INDEX approvals_one_accept_per_run
    ON approvals (run_id) WHERE decision = 'approve';

CREATE TABLE commits (
    id                       TEXT NOT NULL,
    tenant_id                TEXT NOT NULL,
    workbook_id              TEXT NOT NULL,
    run_id                   TEXT NOT NULL UNIQUE,
    approval_id              TEXT NOT NULL UNIQUE REFERENCES approvals (id),
    transaction_id           TEXT,
    transaction_revision     INTEGER,
    previous_version_id      TEXT,
    version_id               TEXT NOT NULL UNIQUE,
    artifact_sha256          TEXT NOT NULL,
    committed_by             TEXT NOT NULL,
    committed_at             TEXT NOT NULL,
    UNIQUE (tenant_id, id),
    UNIQUE (tenant_id, workbook_id, transaction_id),
    FOREIGN KEY (tenant_id, workbook_id) REFERENCES workbooks (tenant_id, id),
    FOREIGN KEY (tenant_id, version_id) REFERENCES workbook_versions (tenant_id, id)
        DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE committed_document_keys (
    tenant_id              TEXT NOT NULL,
    workbook_id            TEXT NOT NULL,
    exact_duplicate_key    TEXT NOT NULL,
    transaction_id         TEXT NOT NULL,
    commit_id              TEXT NOT NULL,
    PRIMARY KEY (tenant_id, workbook_id, exact_duplicate_key),
    FOREIGN KEY (tenant_id, commit_id) REFERENCES commits (tenant_id, id)
);

-- Idempotency, audit events and model accounting ------------------------------

CREATE TABLE idempotency_keys (
    tenant_id        TEXT NOT NULL,
    actor_id         TEXT NOT NULL,
    route            TEXT NOT NULL,
    key              TEXT NOT NULL CHECK (length(key) BETWEEN 16 AND 128),
    request_sha256   TEXT NOT NULL,
    response_status  INTEGER NOT NULL,
    response_json    TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    expires_at       TEXT NOT NULL,
    PRIMARY KEY (tenant_id, actor_id, route, key)
);

CREATE TABLE events (
    sequence      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id      TEXT NOT NULL UNIQUE,
    tenant_id     TEXT NOT NULL,
    run_id        TEXT,
    attempt_id    TEXT,
    event_type    TEXT NOT NULL,
    state         TEXT,
    payload_json  TEXT NOT NULL,
    created_at    TEXT NOT NULL
);
CREATE INDEX events_tenant_sequence ON events (tenant_id, sequence);
CREATE INDEX events_run_sequence ON events (run_id, sequence);

CREATE TABLE model_calls (
    id                   TEXT PRIMARY KEY,
    tenant_id            TEXT NOT NULL,
    run_id               TEXT,
    purpose              TEXT NOT NULL,
    base_url             TEXT NOT NULL,
    model_id             TEXT NOT NULL,
    prompt_version       TEXT NOT NULL,
    request_sha256       TEXT NOT NULL,
    provider_request_id  TEXT,
    started_at           TEXT NOT NULL,
    duration_ms          INTEGER,
    status               TEXT NOT NULL,
    prompt_tokens        INTEGER,
    completion_tokens    INTEGER,
    response_sha256      TEXT,
    validation_outcome   TEXT NOT NULL,
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, id)
);

-- Cycle-closing foreign keys ---------------------------------------------------
-- Both are deferred so a workbook and its first version can be inserted in one
-- transaction. Nullable columns are not checked until they are set.

ALTER TABLE workbooks
    ADD CONSTRAINT workbooks_current_version_fk
    FOREIGN KEY (tenant_id, current_version_id)
    REFERENCES workbook_versions (tenant_id, id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE workbook_versions
    ADD CONSTRAINT workbook_versions_commit_fk
    FOREIGN KEY (tenant_id, commit_id)
    REFERENCES commits (tenant_id, id) DEFERRABLE INITIALLY DEFERRED;

-- Append-only and immutable rows ----------------------------------------------
-- Enforced in the database, not only in the repository layer.

CREATE TRIGGER events_no_update BEFORE UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION reject_mutation('events are append-only');
CREATE TRIGGER events_no_delete BEFORE DELETE ON events
    FOR EACH ROW EXECUTE FUNCTION reject_mutation('events are append-only');

CREATE TRIGGER approvals_no_update BEFORE UPDATE ON approvals
    FOR EACH ROW EXECUTE FUNCTION reject_mutation('approvals are immutable');
CREATE TRIGGER approvals_no_delete BEFORE DELETE ON approvals
    FOR EACH ROW EXECUTE FUNCTION reject_mutation('approvals are immutable');

CREATE TRIGGER plans_no_update BEFORE UPDATE ON plans
    FOR EACH ROW EXECUTE FUNCTION reject_mutation('plans are immutable');
CREATE TRIGGER plans_no_delete BEFORE DELETE ON plans
    FOR EACH ROW EXECUTE FUNCTION reject_mutation('plans are immutable');

CREATE TRIGGER transactions_no_update BEFORE UPDATE ON transactions
    FOR EACH ROW EXECUTE FUNCTION reject_mutation('transaction revisions are immutable');
CREATE TRIGGER transactions_no_delete BEFORE DELETE ON transactions
    FOR EACH ROW EXECUTE FUNCTION reject_mutation('transaction revisions are immutable');

CREATE TRIGGER accounting_policies_no_update BEFORE UPDATE ON accounting_policies
    FOR EACH ROW EXECUTE FUNCTION reject_mutation('accounting policies are immutable');
CREATE TRIGGER accounting_policies_no_delete BEFORE DELETE ON accounting_policies
    FOR EACH ROW EXECUTE FUNCTION reject_mutation('accounting policies are immutable');

CREATE TRIGGER duplicate_resolutions_no_update BEFORE UPDATE ON duplicate_resolutions
    FOR EACH ROW EXECUTE FUNCTION reject_mutation('duplicate resolutions are immutable');
CREATE TRIGGER duplicate_resolutions_no_delete BEFORE DELETE ON duplicate_resolutions
    FOR EACH ROW EXECUTE FUNCTION reject_mutation('duplicate resolutions are immutable');

CREATE TRIGGER committed_keys_no_update BEFORE UPDATE ON committed_document_keys
    FOR EACH ROW EXECUTE FUNCTION reject_mutation('committed document keys are immutable');
CREATE TRIGGER committed_keys_no_delete BEFORE DELETE ON committed_document_keys
    FOR EACH ROW EXECUTE FUNCTION reject_mutation('committed document keys are immutable');

INSERT INTO schema_migrations (version, applied_at)
VALUES (1, to_char(clock_timestamp() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'));
