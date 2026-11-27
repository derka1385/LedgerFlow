# Database and durable storage

P0 database: SQLite on local disk, foreign keys enabled on every connection, five-second busy timeout, and full synchronous durability for commits. Enable WAL only after verifying the linked SQLite library contains the WAL-reset fix (3.51.3+ or a documented patched/backported build); otherwise use rollback journal mode for the demo. One backend instance and one worker process; concurrent browser requests do not imply multiple databases. Back up with SQLite's backup API or an equivalent consistent checkpointed mechanism, not a bare copy of a live main file while ignoring its WAL. See [the upstream WAL notes](https://sqlite.org/wal.html).

Identifiers are opaque TEXT, timestamps are UTC TEXT, booleans are INTEGER 0/1, money and revisions are INTEGER, canonical contract payloads are UTF-8 TEXT with their SHA-256. Files live outside the database in immutable content-addressed storage. Every tenant-owned row has `tenant_id NOT NULL`; use composite foreign keys or equivalent enforced repository checks to prevent linking objects across tenants. All externally addressed queries scope tenant and permission before returning content.

## Tables

The following table definitions are normative schema specifications. Add indexes named below. JSON columns contain only the corresponding validated contract revision, never arbitrary executable content.

| Table | Fields and constraints |
|---|---|
| tenants | `id PK`, `name`, `created_at`, `daily_upload_limit`, `max_queued_runs`; nonnegative quotas |
| users | `id PK`, `tenant_id FK`, `display_name`, `role` employee/accountant/owner, `active`, `created_at`; unique `(tenant_id,id)` |
| invites | `id PK`, `tenant_id FK`, `user_id FK`, `token_hash UNIQUE`, `expires_at`, nullable `consumed_at`, `created_at`; role comes from user, not request |
| sessions | `id PK`, `tenant_id FK`, `user_id FK`, `token_hash UNIQUE`, `csrf_token_hash`, `created_at`, `expires_at`, nullable `revoked_at`; no plaintext session/invite token |
| upload_assignments | `tenant_id`, `user_id`, `workbook_id`, `can_upload`, `created_at`; composite PK `(tenant_id,user_id,workbook_id)` |
| blobs | `tenant_id`, `sha256`, `kind`, `byte_length`, `storage_object_id`, `created_at`, nullable `deleted_at`; PK `(tenant_id,sha256,kind)`; bytes >0 and under kind limit; no user-supplied path |
| workbooks | `id PK`, `tenant_id FK`, `display_name`, `created_by`, `created_at`, nullable `current_version_id`, nullable `active_mapping_id`, `revision`, `status`; unique `(tenant_id,id)` |
| workbook_versions | `id PK`, `tenant_id`, `workbook_id FK`, `sequence`, nullable `parent_version_id`, `blob_sha256`, `source` upload/agent_commit, nullable `commit_id`, `created_by`, `created_at`; unique `(workbook_id,sequence)` and `(tenant_id,id)` |
| inspections | `id PK`, `tenant_id`, `workbook_id`, `version_id`, `inspector_version`, `manifest_sha256`, `baseline_report_sha256`, `status`, `payload_json`, `created_at`; unique `(version_id,inspector_version)` |
| accounting_policies | `id PK`, `tenant_id`, `workbook_id`, `revision`, `payload_json`, `sha256`, `confirmed_by`, `confirmed_at`; unique `(workbook_id,revision)`; immutable |
| mappings | `id PK`, `tenant_id`, `workbook_id`, `revision`, `source_sha256`, `layout_sha256`, `policy_id`, `payload_json`, `mapping_sha256`, `status`, nullable `confirmed_by`, nullable `confirmed_at`; unique `(workbook_id,revision)` |
| documents | `id PK`, `tenant_id`, `workbook_id`, `uploaded_by`, `original_blob_sha256`, nullable `normalized_blob_sha256`, `client_upload_id`, `status`, `created_at`; unique `(tenant_id,uploaded_by,client_upload_id)` |
| transactions | `id PK`, `tenant_id`, `workbook_id`, `document_id`, `revision`, `payload_json`, `payload_sha256`, `exact_duplicate_key`, nullable `semantic_duplicate_key`, `review_status`, `created_at`; PK implementation may use `(id,revision)`; unique `(tenant_id,id,revision)`; immutable revisions |
| duplicate_resolutions | `id PK`, `tenant_id`, `transaction_id`, `transaction_revision`, `related_transaction_id`, `decision`, `reason`, `actor_id`, `created_at`; immutable audit; distinct override never edits raw duplicate key |
| runs | `id PK`, `tenant_id`, `workbook_id`, `document_id`, nullable `transaction_id`, nullable `transaction_revision`, `created_by`, `state`, `state_reason`, `revision`, `base_version_id`, `base_sha256`, `mapping_id`, `policy_id`, nullable `plan_id`, `attempt_count`, `model_request_count`, `active_elapsed_ms`, `cancel_requested`, `created_at`, `updated_at`, nullable `review_expires_at`, nullable `approval_expires_at`; counters bounded per runtime policy |
| jobs | `id PK`, `tenant_id`, `kind` inspect/normalize/map/run, nullable `run_id`, `target_id`, `state` queued/leased/done/failed/cancelled, `available_at`, nullable `lease_owner`, nullable `lease_expires_at`, `epoch`, `revision`, `payload_json`, `created_at`; at most one live job per `(kind,target_id)` |
| workbook_execution_locks | `workbook_id PK`, `tenant_id`, `run_id`, `job_id`, `epoch`, `lease_expires_at`; only protects active execution/preparation, not human wait |
| plans | `id PK`, `tenant_id`, `run_id`, `revision`, `payload_json`, `plan_sha256`, `mapping_sha256`, `transaction_revision`, `created_at`; unique `(run_id,revision)`; immutable |
| attempts | `id PK`, `tenant_id`, `run_id`, `number`, `job_epoch`, `code_blob_sha256`, `plan_sha256`, `image_digest`, `runtime`, `runtime_policy_version`, `supervisor_job_id UNIQUE`, `state`, nullable `exit_code`, nullable `termination_reason`, nullable `started_at`, nullable `finished_at`, nullable `duration_ms`, nullable `peak_memory_bytes`, `cleanup_status`, nullable `cleanup_at`; unique `(run_id,number)` |
| artifacts | `id PK`, `tenant_id`, `run_id`, nullable `attempt_id`, `kind` candidate/code/log/report/diff/evidence, `blob_sha256`, `byte_length`, `frozen_at`, `created_at`, `expires_at`; candidate mutable only before frozen_at, never referenced by approval while unfrozen |
| validation_reports | `id PK`, `tenant_id`, `run_id`, `attempt_id`, `candidate_sha256`, `base_sha256`, `plan_sha256`, `mapping_sha256`, `verifier_version`, `payload_json`, `report_sha256`, `host_attestation_sha256`, `result`, `created_at`; unique `(attempt_id,candidate_sha256,verifier_version)` |
| approvals | `id PK`, `tenant_id`, `run_id`, `actor_id`, `decision`, `base_version_id`, `base_sha256`, `candidate_sha256`, `plan_sha256`, `mapping_sha256`, `validation_report_sha256`, `policy_version`, `tuple_sha256`, nullable `comment`, `created_at`, `expires_at`; immutable; at most one accepted approval per run |
| commits | `id PK`, `tenant_id`, `workbook_id`, `run_id UNIQUE`, `approval_id UNIQUE`, `transaction_id`, `transaction_revision`, `previous_version_id`, `version_id UNIQUE`, `artifact_sha256`, `committed_by`, `committed_at`; unique `(tenant_id,workbook_id,transaction_id)` |
| committed_document_keys | `tenant_id`, `workbook_id`, `exact_duplicate_key`, `transaction_id`, `commit_id`; PK `(tenant_id,workbook_id,exact_duplicate_key)`; prevents same source posting via a second transaction ID |
| idempotency_keys | `tenant_id`, `actor_id`, `route`, `key`, `request_sha256`, `response_status`, `response_json`, `created_at`, `expires_at`; composite PK `(tenant_id,actor_id,route,key)` |
| events | `sequence INTEGER PRIMARY KEY AUTOINCREMENT`, `event_id UNIQUE`, `tenant_id`, nullable `run_id`, nullable `attempt_id`, `event_type`, `state`, `payload_json`, `created_at`; append-only through application repository |
| model_calls | `id PK`, `tenant_id`, nullable `run_id`, `purpose`, `base_url`, `model_id`, `prompt_version`, `request_sha256`, nullable `provider_request_id`, `started_at`, `duration_ms`, `status`, nullable `prompt_tokens`, nullable `completion_tokens`, nullable `response_sha256`, `validation_outcome`; no key/full private prompt in public logs |

Foreign-key cycles between workbooks/current versions and versions/commits can be deferred or inserted in a prescribed sequence within one transaction. Never disable foreign keys to work around them. Store a nullable current version only during initial workbook creation; ready workbooks require a valid current version.

`transactions` uses a composite primary key `(id,revision)`; `id` alone is not a unique revision row. References to a specific extraction/confirmation always include both. Commits additionally enforce one committed transaction identity across revisions. This prevents a corrected revision from being posted again as if new.

## Required indexes

* `runs(tenant_id,created_at,id)` and `runs(workbook_id,state)`.
* `jobs(state,available_at,lease_expires_at)` and a partial unique index on `(kind,target_id)` where state is queued or leased.
* `events(tenant_id,sequence)` and `events(run_id,sequence)`.
* `sessions(token_hash)` and `sessions(expires_at)`.
* `transactions(tenant_id,workbook_id,semantic_duplicate_key)`; this is an index, not automatically a uniqueness constraint because distinct transactions can share a heuristic key.
* `documents(tenant_id,original_blob_sha256)` and `artifacts(run_id,kind)`.
* `workbook_versions(workbook_id,sequence DESC)` and `attempts(run_id,number)`.

## Job leases and restart protocol

Claim the oldest available job in a short write transaction, changing queued/expired-leased state conditionally and increasing epoch. Renew lease every five seconds with a 20-second expiry. An expired worker loses authority to publish results. All result writes compare epoch and expected run revision. The supervisor also records attempt ID, epoch and its own absolute 60-second deadline.

On restart reconcile running attempts with supervisor inventory before scheduling any replacement. If a known job is still active, adopt observation under the new lease or terminate it. Never create a second active container merely because an RPC response was lost. Uncertainty blocks the run until reconciled.

The execution lock is leased and fenced. It ends when a candidate is frozen/verified or the attempt fails; it does not extend through approval. Another run may then produce a candidate from the same base, but only one can commit under compare-and-swap.

## Duplicate and idempotency rules

1. Client upload key handles mobile retries; exact-byte document hash catches identical reuploads.
2. Before planning, search committed exact-byte keys in the same workbook. Return the prior commit rather than creating a new posting.
3. A semantic key uses normalized merchant/reference/date/currency/gross. If reference is absent, label it a possible duplicate. A different photo can produce a different byte hash for the same receipt.
4. Possible duplicates require accountant resolution. Distinct overrides record who/why and the related transaction. They never override an exact-byte committed duplicate in P0.
5. At commit recheck uniqueness inside the write transaction; preflight duplicate checks alone are race-prone.

## Filesystem consistency

Tenant-specific content-addressed namespace: object IDs map internally to `objects/<tenant>/<kind>/<sha256>`. Access is only through authorized server lookups, never an exposed static directory. Reject links and ensure storage root is an actual configured directory. Use create-exclusive temporary files, fsync, atomic same-filesystem rename, immutable permissions and parent-directory fsync. The app's own artifact store is not mounted into a workload.

The database current-version pointer is authoritative. Write artifact first, then commit pointer/commit/audit atomically. Unreferenced blobs can be garbage-collected after a grace period; do not delete a blob referenced by any version, pending approval or retained evidence. Crash tests cover every boundary.

## Retention and audit

P0 policy: failed staging immediately removed after bounded evidence capture; candidates expire after 24 hours if uncommitted; normalized/original receipts and run evidence retained seven days for the demo tenant; committed versions retained until owner deletion/export policy is defined. These are proposed settings, not a legal accounting retention policy. Do not use real company books under this demo policy.

Application code can append events but offers no edit/delete endpoint for audit rows. File/report hashes reveal accidental changes and bind approvals. This is not an externally anchored, tamper-proof ledger: a compromised host administrator could rewrite DB and files. Export an evidence bundle at submission and retain a backup separately.

## Migration to production

Use numbered schema migrations committed with each event-time release. On startup reject a database newer than the running code supports. A single VM can handle modest workload if measured; for multiple hosts use PostgreSQL row locks/transactions and an object store with immutable keys. Introduce proper identity federation and tenant isolation before opening public uploads at scale.
