# Automated test and evidence plan

This is a test specification for event-time implementation. **None of these application/runtime tests has been executed in preparation.** Read-only workbook inspection and document checks are recorded separately in [VERIFICATION](VERIFICATION.md).

Use pytest for deterministic domain/API tests, property tests only where they exercise real invariants, and actual Vultr Docker/runsc jobs for containment. Mocked model responses help test control flow; they never establish model reliability or hackathon runtime compliance.

## Fixture specifications to create after coding permission

| Fixture | Required characteristics |
|---|---|
| T1 balanced T-accounts | 32 or a documented smaller chart, blocks arranged horizontally/vertically, bracketed contra refs, blank styled slots, opening balances, two-row merged headers |
| T2 extension preservation | Standard and x14 validation, unknown inert XML part, workbook structure lock, binary printer part, formula cells, calc chain |
| J1 journal | Stable date/reference/account/description/debit/credit headers, reordered columns, preformatted blank rows, existing historical rows |
| J2 alternate journal | Amount + explicit side convention, 1904 date system, renamed sheet/header synonyms |
| R1 clear receipt | Known SEK 125.00 gross, 100.00 net, 25.00 tax, explicit office-supplies context; payment/tax policy separately confirmed |
| R2 ambiguity | Blurred amount or missing VAT, employee-card ambiguity, source text containing a harmless prompt-injection sentence |
| W1 hostile package | Bounded test archive with duplicate name/path traversal/entity/active-link variants, designed not to consume host resources |

Do not copy the actual student workbook into a public fixture directory. A local private regression may use its known hash with permission; the public suite uses newly authored redacted workbooks. Keep hostile test samples small and controlled.

## P0 financial and Excel tests

| ID | Setup/action | Required assertion |
|---|---|---|
| F01 | Admit 10,000 debit supplies + 2,500 debit tax + 12,500 credit bank | Exact balance; correct account IDs and policy; no float tolerance |
| F02 | Change any line by one minor unit | Admission rejects imbalance |
| F03 | Unknown tax or payment source | NEEDS_REVIEW; no sandbox launched |
| F04 | Missing chart account or mismatched currency | Reject; no generic account substitution |
| F05 | Compound entry expanded to two bank credit rows | Allocation edges conserve each line and contra refs exactly |
| F06 | Same total assigned to wrong debit account | Independent validator fails, despite balanced overall sum |
| F07 | Existing numerical zero in a target pair | Treated as occupied; not overwritten |
| F08 | Reference filled but amount blank | Hold for mapping review, not an empty slot |
| F09 | No eligible row left | NO_SAFE_SLOTS; no row insertion or source changes |
| X01 | Inspect T1 with reordered block positions/two-row headers | Mapping derives correct rows/columns from evidence; no coordinate hardcoding |
| X02 | Confirm J1/J2 with different column order/date system | Correct typed dates/amounts; existing rows unchanged |
| X03 | Routine successful append | Static map reused; fresh occupancy computed; no LLM remap |
| X04 | Rename sheet/change merge/formula/instruction | MAPPING_DRIFT; old map cannot execute |
| X05 | Modify T2 one approved posting | Every nonallowed member hash unchanged; x14 bytes, protection, names and printer data preserved |
| X06 | Drop x14 validation or change style in candidate | Verifier fails, even when all amounts match |
| X07 | Add unrelated cell, sheet or extra archive member | Exact-write-set/package failure |
| X08 | Generated manifest lies about modified cells | Actual complete before/after diff catches it |
| X09 | Write receipt text beginning `=`, `+`, `-`, `@` | Explicit literal text, no new `<f>` formula; no external link |
| X10 | New input intersects legacy formula-posting dependency | Block unless supported separate workflow; P0 never mutates historical posting |
| X11 | Source baseline inconsistent but displayed W24=0 | Report actual discrepancy; no global balanced label |
| X12 | Unknown/signed/encrypted/active workbook | Named refusal; never silently strip features |
| X13 | Open output in native Excel on disposable copy | No repair warning; dropdown validation, merges, formatting and protection remain; recalc behavior documented |
| X14 | Target cells absent/ambiguous XML or unsupported encoding | Writer safely refuses rather than regex-rebuilding workbook |
| X15 | Formula text preserved with stale cached value | UI labels cache limitation; no claim of fresh native recalculation |

For the private actual SSE baseline, independently expect opening debits/credits 1,220,000 each; full mapped debits 1,908,465, credits 1,820,489, difference 87,976. Formula-valued postings must be evaluated from literal precedents, not merely read as caches. Private test failures never authorize silently correcting the workbook.

## P0 isolation tests on deployed Vultr

| ID | Action | Evidence/pass criterion |
|---|---|---|
| S01 | Protected host dummy read plus readable control | Control succeeds; protected file existed on host, read fails; host hash unchanged; exact binds recorded |
| S02 | Fixed infinite loop, diagnostic timeout 5 s | Whole container terminated by ≤7 s; no orphan; app liveness responses ≤2 s during test |
| S03 | Public IP, DNS and metadata-network probes | Connections fail under no-network policy; no external service dependence |
| S04 | Inspect env and expected secret names inside workload | No inherited key/credential value; don't publish real key for comparison |
| S05 | Check Docker socket and app paths | Absent/inaccessible; no parent-store mount |
| S06 | Attempt root filesystem write | Fails; `/work` allowed; source copy remains read-only |
| S07 | Bounded memory allocation over limit | OOM/limit observed from host; application stays healthy |
| S08 | Controlled process creation above PID limit | Limit enforced; job cleanup removes all descendants |
| S09 | Bounded log flood above policy | Capture capped/truncation signaled; host disk not filled |
| S10 | Output symlink, FIFO, hardlink or unexpected file | Collector rejects without blocking/read-through |
| S11 | Work area fills to quota | Failure bounded at configured mount capacity; host normal jobs recover |
| S12 | Stop worker mid-execution | Supervisor deadline/reaper destroys job without worker cooperation |
| S13 | Forge workload output claiming validator pass | Only separate verifier report/host attestation accepted |
| S14 | Attempt supervisor image/mount/argv override | Protocol rejects; no unsafe job created |
| S15 | Runtime identity check | Host configuration shows runsc and actual limits; no reliance on spoofable guest uname/dmesg |

Do not run uncontrolled fork bombs or resource attacks. Use bounded diagnostic programs and one probe at a time. A local OS subprocess timeout does not satisfy S02.

## P0 API, persistence and approval tests

| ID | Action | Required assertion |
|---|---|---|
| A01 | Unauthenticated upload/run/approve | 401; public landing still works |
| A02 | Employee approves or changes policy | 403; employee can correct allowed source fields only |
| A03 | Tenant B reads Tenant A workbook/run/artifact/events | 404; no metadata leakage |
| A04 | Missing/wrong CSRF or foreign Origin | Rejected mutation |
| A05 | Repeat same upload/run/approval idempotency key | Same original result; one mutation |
| A06 | Same key, different body/file | 409 IDEMPOTENCY_CONFLICT |
| A07 | Same receipt photo posted again after commit | Existing commit/ALREADY_COMMITTED; no new workbook write |
| A08 | Different photo of same reference/date/total | DUPLICATE_REVIEW; explicit resolution required |
| A09 | Two concurrent approvals on same base | Exactly one current-pointer update; other STALE_BASE |
| A10 | Candidate changed/replaced after review | Hash mismatch; no commit |
| A11 | Old mapping/policy/report hash approved | Refused; fresh review required |
| A12 | Approval response lost then retried | Same commit/version; no duplicate posting |
| A13 | Crash before artifact fsync, after artifact persistence, before DB commit, after DB commit | Current pointer always references durable correct bytes; orphans safe to collect; one recoverable commit |
| A14 | Cancel during execution, validation or approval race | Cancellation serialized; no late callback commits; resources destroyed |
| A15 | Lease expires, old worker returns late | Fencing rejects stale result |
| A16 | Supervisor create response lost | Lookup by attempt ID avoids duplicate job |
| A17 | Cleanup fails | No AWAITING_APPROVAL or commit; explicit cleanup state |
| A18 | SSE drops and reconnects | Durable events/snapshot restore exact current state, no duplicated UI mutation |
| A19 | SQLite lock contention | Bounded retry/error; no transaction held during LLM or human wait |
| A20 | Active job limits/queue/day limits exceeded | 429 or queue response; app remains responsive |

## VSI capability tests and mocks

Live gate: chosen model ID entitlement; one actual image; strict object response; unknown-field behavior; integer amount representation; generated code execution; provider timeouts/429. At least three representative receipts must produce correct observable fields before selecting a default. Three examples are a smoke gate, not an accuracy benchmark.

Automated model stubs exercise invalid JSON, extra fields, string amounts, missing evidence, refusal, truncation, 429, timeout, ordinary Python error followed by repair, and disallowed policy changes. Mark stub runs `simulated_provider`; exclude them from live demo evidence. Do not call offline prompt checks “tested VSI.”

## Test order during event

1. First 90 minutes: S01/S02/S15 plus actual VSI smoke gate and deployed HTTPS.
2. Before UI integration: F01/F02/F05/F06, X05/X06/X08, A05/A09/A10/A12.
3. Before demo recording: happy path on both layout families, S01/S02 recovery, X13 native opening, A03 tenant boundary, A17 cleanup gate.
4. Before submission: replay recorded scenario once from fresh state, verify public URL, artifact downloads, repository instructions and video link.

All P0 assertions affecting a claimed feature must pass. A feature that fails is removed or explicitly marked unsupported. Never weaken containment or approval checks to keep a visual demonstration moving.

## Evidence bundle format

Each real run bundle contains a manifest with run/attempt IDs, timestamps, source commit, host instance/region, actual runtime/image/policy versions, provider model/request metadata, code/plan/base/candidate/report hashes, bounded logs, exact diff, cleanup status and approval/commit result if any. Store private input objects separately; publish sanitized examples only.

Containment bundle adds dummy-file creation/hash/permissions, actual host runtime inspection, probe log/exit/elapsed time, app liveness trace, before/after original/current hashes, destruction confirmation and a subsequent successful normal job. Link every claim in the video or README to this real evidence.

Record a test results table with `test_id`, `environment`, `result` pass/fail/not_run, `observed_at`, `source_commit`, `evidence_path`, `limitation`. `not_run` is never rendered as pass. Documentation lint and cost arithmetic checks belong to preparation verification, not application test results.
