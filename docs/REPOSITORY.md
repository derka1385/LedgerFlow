# Repository layout, interfaces and dependencies

The current tree contains documentation/research only. The following paths are the **event-time implementation target**, not existing code.

## Target tree and ownership

| Path | Owner | Responsibility |
|---|---|---|
| `frontend/` | UI developer | React application, mobile capture, onboarding/review/result screens |
| `backend/ledgerflow/api/` | Backend developer | FastAPI routers, sessions, CSRF, authorization, serializers |
| `backend/ledgerflow/domain/` | Backend developer | Strict data contracts, money, policy, duplicate rules, states |
| `backend/ledgerflow/orchestrator/` | Backend developer | Durable worker, VSI client, prompts, budgets, transitions |
| `ledgerflow/persistence/` | Backend developer | PostgreSQL connection pool, migrations, exact-artifact commit |
| `excel_engine/` | Excel developer | Package inspection, adapters, slot allocator, narrow writer helper |
| `verifier/` | Excel developer | Independent diff, preservation and accounting checks |
| `sandbox_supervisor/` | Runtime developer | Fixed local protocol, hardening, lifecycle, collection, reaper |
| `infra/` | Runtime developer | Event-authored images, service/proxy config, deployment runbook commands |
| `contracts/` | Backend owns, others review | Versioned JSON/OpenAPI contract exports once implemented |
| `tests/domain/` and `tests/api/` | Backend developer | Money, policy, concurrency, authorization |
| `tests/excel/` | Excel developer | Mapping, preservation, hostile package cases |
| `tests/runtime/` | Runtime developer | Real containment and lifecycle evidence |
| `fixtures/synthetic/` | Excel developer | Newly authored redacted fixtures after event coding starts |
| `docs/` | Lead | Specifications and final honest evidence index |

Each owner keeps changes in their directory. The API/contract owner resolves shared contract changes immediately. One person owns each migration and dependency lockfile; do not have four people independently change root dependencies. Integrate narrow interface stubs **during the event**, then replace with real behavior before any claim of execution.

## Interface freeze at 10:30

| Interface | Inputs | Outputs / invariants |
|---|---|---|
| Inspector `inspect_workbook` | Immutable source bytes ID/hash, inspector version | Bounded package/evidence manifest, baseline analysis, compatibility/refusal |
| Adapter `propose_mapping` | Manifest + optional VSI proposal | Typed mapping proposal; source anchors, no write authority |
| Mapping `confirm` | Owner bindings + exact source/map/policy revisions | Immutable confirmed mapping; layout hash; baseline acknowledgement |
| Accounting `admit_entry` | Confirmed TransactionV1, policy, chart | EntryV1 or review reason; exact minor-unit conservation |
| Slots `reserve_operations` | Source version + confirmed map + EntryV1 | Exact CellOperationV1 set and contra allocation, or safe refusal |
| VSI `extract` | Normalized image + extraction schema/prompt version | Validated extraction proposal, request/model/usage metadata |
| VSI `plan_and_code` | Transaction, mapping subset, policy, safe slots | Entry proposal, operations, explanation and Python; no server authority |
| Supervisor `execute` | Fixed kind, attempt/epoch, input IDs/hashes | Actual exit/log/resource/output/cleanup envelope |
| Verifier `verify` | Read-only base/candidate + admitted plan/map/policy | ValidationReportV1 with complete observed diff, not generated claims |
| Commit `approve_and_commit` | Authorized actor + ApprovalRequestV1 + idempotency key | CommitV1, rejection, or named conflict; never rerun code |

File bytes can cross only through staged object IDs resolved by trusted code. Internal Python APIs can use validated model types; the supervisor protocol is bounded JSON. Do not import generated modules into API/worker/verifier to share data.

## Writer helper contract

The execution image exposes a versioned `ledgerflow_workbook` helper with these low-level capabilities: open a read-only package; retrieve a typed cell snapshot; patch an existing supported cell's literal payload; emit a candidate ZIP preserving non-target bytes; emit a nonauthoritative operation manifest. Each operation uses sheet ID/name, cell, expected-before snapshot and typed-after payload.

The helper does not extract receipts, choose accounts, infer tax, allocate money, approve or commit. Generated Python performs the plan-specific sequence using that helper and outputs `/work/candidate.xlsx`. It may be buggy or malicious; the independent verifier still checks the actual bytes. This is adaptive mapping plus executed generated code, not a hardcoded receipt-to-fixed-template function.

## Dependency selection

Registry observations below were fetched on 26 November 2026 and saved in `research/dependency-catalog-2026-11-26.json`. They are **candidate versions, not an installed/tested lockfile**. During the event resolve a compatible set on Python 3.12/Ubuntu 24.04, commit exact locks/hashes, and run the meaningful tests before freezing. Do not upgrade simply to chase “latest.”

| Package | Observed version | Use / decision |
|---|---|---|
| FastAPI | 0.165.0 | REST API; avoid unnecessary plugins |
| Pydantic | 2.14.4 | Strict models, unknown-field rejection, schema export |
| Uvicorn | 0.54.0 | ASGI server, one API process initially |
| HTTPX | 0.29.0 | Small explicit VSI HTTP client; no full agent SDK needed |
| python-multipart | 0.0.34 | Bounded upload parsing; also enforce upstream/stream byte limits |
| Pillow | 13.0.0 | Isolated image normalization only |
| defusedxml | 0.7.1 | Secure XML handling; explicit parser/resource configuration still required |
| openpyxl | 3.1.5 | Optional read convenience/simple classified profiles, not SSE preservation writer |
| pytest | 9.2.0 | Domain/API and controlled integration tests |
| Hypothesis | 6.170.17 | Optional money/allocation/property invariants after core tests |
| React | 19.3.1 | Product UI; pair react-dom version during resolution |
| TypeScript | 7.0.2 | Typed client contracts; existing team-supported version may be safer |
| Vite | 8.4.0 | Static build; observed Node engine `^20.19.0 || >=22.12.0` |
| Tailwind CSS | 4.3.5 | Styling; confirm matching Vite integration package |

Primary registry sources: [PyPI FastAPI metadata](https://pypi.org/pypi/fastapi/json), [PyPI Pydantic metadata](https://pypi.org/pypi/pydantic/json), [PyPI openpyxl metadata](https://pypi.org/pypi/openpyxl/json), [npm React metadata](https://registry.npmjs.org/react/latest), [npm Vite metadata](https://registry.npmjs.org/vite/latest). The saved registry file lists every queried source, response digest and interpreter/engine requirement.

Python 3.12 meets the observed Python minimums for these candidates, but transitive compatibility is untested. Use a maintained Node LTS meeting the actual Vite/plugin engines and record its version. Keep runtime Docker/gVisor/Caddy versions pinned after official-source installation and deployed compatibility tests; no versions were fabricated here.

SQLite comes through the Python/OS runtime. Check `sqlite_version` and distribution patches before WAL; [SQLite documents a WAL-reset fix in 3.51.3 and selected backports](https://sqlite.org/wal.html). If patch provenance is unclear, use rollback journal mode for this event. A Python package version does not identify the linked SQLite library.

## Frontend delivery specification

Four main views suffice:

1. **Workbook onboarding:** filename/version, supported/unsupported features, recognized sheets/accounts, highlighted write regions, baseline warning, explicit mapping/policy confirmation. No fake universal-compatibility badge.
2. **Mobile upload:** assigned workbook, camera/file picker, readable preview, upload progress, clear missing-field correction. Preserve client upload ID across retries. No offline queue in P0.
3. **Run review:** receipt evidence and editable structured fields, ordered stage timeline, generated-code drawer, real stdout/stderr, entry lines, independently derived cell diff, limitations, approve/reject for accountant. Employee sees progress without approval controls.
4. **Result/history:** committed version/hash, source receipt/run linkage, download workbook and audit JSON, original-version availability, subsequent runs. A generated preview and a committed version have different labels.

Phone layout uses one column and comfortable tap targets. Desktop review can use document/entry side-by-side with a collapsible evidence pane. Use plain labels and honest pending/failed states; logs do not imply successful validation. Escape all document and log text. No workbook blobs/session tokens in localStorage or a service-worker cache. Keyboard access, visible focus, contrast and status text are P0; visual animation is optional.

## Integration discipline

Use one short-lived branch per owner, merge at agreed checkpoints, and protect the shared happy path. Contract changes include examples and the consumers' updates in one small integration. Do not add opaque client-generated financial state; server snapshots are authoritative. Tag the recorded-demo commit and record any deviations from these specifications in final event documentation.
