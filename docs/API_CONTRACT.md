# API contract

Base path `/api/v1`, same HTTPS origin as the UI. JSON uses [DATA_SCHEMAS](DATA_SCHEMAS.md). IDs are opaque. API responses never reveal filesystem paths, keys or Docker details. All monetary amounts are integer minor units.

## Authentication, tenant scope and errors

P0 uses locally provisioned random 256-bit single-use invites with server-assigned tenant/role. An invite is exchanged once for a random session cookie; store token hashes only. Roles: `employee` (own document upload/run visibility), `accountant` (tenant-wide review and approval), `owner` (accountant plus workbook/policy/mapping setup). A session cannot choose its tenant. Use `__Host-ledgerflow_session`, Secure, HttpOnly, SameSite=Lax, Path=/, eight-hour expiry and revocation on logout.

State-changing endpoints require the same-origin `Origin` and a session-bound `X-CSRF-Token`. An invite exchange also checks Origin. Do not put bearer/session/invite tokens in query strings or logs. CORS is same-origin only; no wildcard credentials. Fetch snapshots and SSE are authorized by the same session. Cross-tenant IDs return 404; same-tenant insufficient role returns 403.

Error envelope, with no stack trace:

```json
{
  "error": {
    "code": "STALE_BASE",
    "message": "This workbook changed after the preview. Create a new run and approve its result.",
    "retryable": false,
    "request_id": "req_demo_1",
    "details": {"current_version_id":"ver_demo_2"}
  }
}
```

Status mapping: 400 malformed request/unsupported fields; 401 missing/expired session; 403 role/CSRF; 404 unknown/inaccessible object; 409 state/idempotency/conflict/duplicate; 410 expired candidate or pairing token; 413 byte/pixel/package bound; 415 unsupported file; 422 semantic/mapping/accounting failure; 429 rate/queue quota; 503 temporary inference/runner unavailability. Failed asynchronous work is also represented durably in run state; HTTP 202 is not execution success.

## Common mutation rules

Require `Idempotency-Key` on uploads, run creation, corrections, mapping confirmation, approval and cancellation. Key is 16–128 ASCII characters, tenant + actor + route scoped, retained seven days. Store canonical request hash plus outcome in the same transaction as the mutation. Identical key/body returns the original result with `Idempotent-Replayed: true`; different body returns 409 `IDEMPOTENCY_CONFLICT`. For multipart uploads hash exact file bytes and canonical metadata.

Use explicit expected revision/version fields for updates. Never take tenant ID, user role, validation result or artifact filesystem path from a request. Lists use opaque `cursor`, `limit` 1–100 (default 25), returning `items` and nullable `next_cursor`.

## Endpoints

| Method and route | Permission | Input | Response / behavior |
|---|---|---|---|
| POST `/auth/session` | Invite bearer, no prior session | `{invite_token}` | 201 session cookie + `{user_id,role,tenant_id,csrf_token,expires_at}`; invite consumed atomically |
| GET `/auth/session` | Any session | None | 200 current session metadata and CSRF token |
| DELETE `/auth/session` | Any session | CSRF | 204, revoke server session and clear cookie |
| POST `/workbooks` | Owner | Multipart `file`, `display_name` max 120 | 202 `{workbook_id,version_id,sha256,status:"inspecting"}`; owner-scoped inspection job |
| GET `/workbooks` | Accountant/owner | Cursor | 200 permitted workbook list/current versions |
| GET `/workbooks/{id}` | Accountant/owner | None | 200 metadata, current version/hash, mapping status, compatibility/baseline summary |
| GET `/workbooks/{id}/inspection` | Accountant/owner | None | 200 bounded inventory and baseline report; 409 if incomplete |
| POST `/workbooks/{id}/mapping-proposals` | Owner | `{base_version_id,base_sha256}` | 202 mapping analysis job ID; reuses compatible existing proposal without new LLM call |
| GET `/workbooks/{id}/mappings/{mapping_id}` | Accountant/owner | None | 200 WorkbookMappingV1 plus bounded source evidence |
| POST `/workbooks/{id}/mappings/{mapping_id}/confirm` | Owner | `{expected_mapping_version,expected_mapping_sha256,policy_version,confirmed_bindings,baseline_acknowledgement}` | 200 new immutable confirmed mapping revision; never mutates hash in place |
| POST `/workbooks/{id}/documents` | Employee/accountant/owner | Multipart JPEG/PNG `file`, `client_upload_id` | 202 `{document_id,sha256,status:"normalizing"}`; employee must have upload assignment to workbook |
| GET `/upload-targets` | Any session | None | 200 assigned workbook names/IDs plus permitted current base hash/version and mapping ID/revision; no financial cells; supports employee run creation without accountant-only workbook access |
| GET `/documents/{id}` | Uploader or accountant/owner | None | 200 status, permitted image URL, extraction/review status |
| POST `/runs` | Authorized uploader/accountant/owner | CreateRunV1 below | 202 `{run_id,state,events_url}`; requires confirmed map and normalized image |
| GET `/runs` | Employee own; accountant/owner tenant | Optional workbook/state/cursor | 200 permitted runs, summaries only |
| GET `/runs/{id}` | Same scope | None | 200 RunSnapshotV1; authoritative revision + last event sequence |
| GET `/runs/{id}/events` | Same scope | `Last-Event-ID` header or `after` cursor | SSE stream; durable replay; see below |
| POST `/runs/{id}/corrections` | Uploader for receipt fields; accountant/owner for policy/payment/accounts | `{expected_run_revision,expected_transaction_revision,corrections,reason}` | 202 new transaction revision and rerun within policy; old plan/candidate invalidated |
| POST `/runs/{id}/duplicate-resolution` | Accountant/owner | `{expected_run_revision,decision:"same_transaction" or "distinct_transaction",reason}` | 200 held duplicate resolved; same transaction ends without posting, distinct linked to audited override |
| POST `/runs/{id}/cancel` | Creator or accountant/owner | `{expected_run_revision,reason}` | 202 cancellation; supervisor kills job before terminal acknowledgement; 409 after commit |
| GET `/runs/{id}/diff` | Uploader or accountant/owner | None | 200 independently computed diff/report only after validation |
| POST `/runs/{id}/approval` | Accountant/owner | ApprovalRequestV1 | 200 CommitV1 for successful approve-and-commit; 200 rejected run for rejection; 409 stale or mismatched hash |
| GET `/artifacts/{id}/download` | Authorized run/workbook reader | None | Frozen file bytes; content hash ETag and attachment filename; no directory reads |
| GET `/workbooks/{id}/versions` | Accountant/owner | Cursor | 200 version list with provenance |
| GET `/health/live` | Public | None | 200 process alive; no secrets/versions |
| GET `/health/ready` | Operations only | None | 200 dependencies ready, 503 otherwise; no generated-code execution |

Mapping confirmations only allow bindings that pass deterministic inspection; the owner cannot grant arbitrary host paths or waive containment policy. `confirmed_bindings` is a typed subset of WorkbookMappingV1 fields, not freeform Python. Unknown or changed feature constraints still block confirmation.

### Create run

```json
{
  "workbook_id": "wb_demo_1",
  "document_id": "doc_demo_1",
  "expected_base_version_id": "ver_demo_1",
  "expected_base_sha256": "1111111111111111111111111111111111111111111111111111111111111111",
  "mapping_id": "map_demo_1",
  "mapping_version": 1,
  "client_request_id": "mobile_upload_1"
}
```

Source hash here is illustrative. Server compares it against actual bytes. A document still normalizing returns 409 `DOCUMENT_NOT_READY`. Unconfirmed/incompatible mapping returns 409 `MAPPING_REQUIRED`. Exact committed duplicate returns 409 `ALREADY_COMMITTED` with an authorized existing commit reference. Fuzzy/semantic duplicate transitions into `DUPLICATE_REVIEW`; it is never silently skipped or posted.

`RunSnapshotV1` contains `run_id`, `revision`, `workbook_id`, `document_id`, `state`, `state_reason`, `base_version_id`, `mapping_version`, `transaction_revision`, `attempt_count`, `last_event_sequence`, nullable `transaction`, nullable `entry`, nullable `plan_sha256`, nullable `validation_summary`, nullable `candidate_artifact_id`, nullable `candidate_sha256`, nullable `commit`, `created_at`, `updated_at`. Large code/log/report objects are separately authorized artifacts. Do not return the entire workbook on each poll.

### Approval is exact and synchronous

The UI retrieves the candidate's frozen hash tuple and sends all ApprovalRequestV1 fields. Approval validity requires state `AWAITING_APPROVAL`, passing mandatory checks, confirmed cleanup, matching current mapping/policy, no unresolved duplicate/receipt fields and the expected current workbook version.

The server records approval and performs the database compare-and-swap in one short request. There is no separate untrusted “commit this path” endpoint. If the response is lost, the same idempotency key returns the existing commit. A new key for an already committed run also returns the existing commit rather than posting again. Rejection freezes the audit and discards candidate availability after retention; it does not modify the workbook.

## Server-sent events

Use `Content-Type: text/event-stream`, `Cache-Control: no-cache, no-transform`, and disable proxy buffering. Browser native EventSource uses the same-origin HttpOnly session cookie. SSE has no financial mutation semantics. Log messages are displayed as escaped plain text.

Example event (illustrative):

```text
id: 104
event: run.state_changed
data: {"schema_version":"ledgerflow.event.v1","event_id":"evt_demo_104","sequence":104,"run_id":"run_demo_1","attempt_id":"att_demo_1","event_type":"run.state_changed","state":"EXECUTING","occurred_at":"2026-11-27T12:00:00Z","message":"Running generated Python in an isolated environment.","data":{"from":"SANDBOX_STARTING","to":"EXECUTING","reason_code":"STARTED"}}

```

Heartbeat every 15 seconds; no heartbeat persistence required. Events persist with the state transition. On reconnect replay permitted events with `sequence > Last-Event-ID`. Clients deduplicate by sequence and reconcile with GET snapshot. If cursor retention expired, return 409 `EVENT_CURSOR_EXPIRED` before streaming and require snapshot refresh. A client must never lose its committed-result state because it missed an SSE event.

SSE access ends when the session expires or loses permission; recheck authorization at least every heartbeat. Each user may open at most three streams. Backpressure disconnects slow clients; it does not accumulate unbounded logs.

## Limits and UX errors

P0: workbook 10 MiB; image 10 MiB original, 20 megapixels decoded, normalized longest edge ≤2,048 pixels and ≤2 MiB; two active jobs per VM; one execution per workbook; ten queued runs per tenant; 50 document uploads/day/tenant; five login attempts/minute/IP. Invite owners can raise quotas via deployment settings, never generated code.

Common actionable codes: `UNSUPPORTED_WORKBOOK`, `ARCHIVE_LIMIT`, `IMAGE_TOO_LARGE`, `IMAGE_UNREADABLE`, `MAPPING_REQUIRED`, `BASELINE_REVIEW_REQUIRED`, `MAPPING_DRIFT`, `NO_SAFE_SLOTS`, `PAYMENT_CONTEXT_REQUIRED`, `TAX_REVIEW_REQUIRED`, `DUPLICATE_REVIEW`, `INFERENCE_UNAVAILABLE`, `SCHEMA_INVALID`, `EXECUTION_TIMEOUT`, `VALIDATION_FAILED`, `CLEANUP_PENDING`, `APPROVAL_HASH_MISMATCH`, `STALE_BASE`, `CANDIDATE_EXPIRED`.

Map errors to specific recovery: replace/rephotograph file, confirm fields, adjust mapping under owner review, wait/retry a transient service, or rerun on current version. Do not expose “try again” for a hard containment violation.

## Optional P1 mobile pairing

Owner POST `/pairings` creates `{pairing_id,fragment_token,expires_at}` with upload-only workbook scope. Phone POST `/pairings/exchange` sends token from the fragment in the body, consumes it atomically, and receives an employee upload session. Owner can DELETE pairing before exchange. Tokens expire in two minutes and are never approval credentials. These routes are not needed to ship P0; independent invited sessions suffice.
