# FRONTEND_HANDOFF — 27 Nov 2026, morning

Owner of this work: frontend, accounting validation rules, synthetic fixtures, product experience.
Codex owns backend, Vultr integration, Excel execution and sandbox infrastructure. **Nothing in `docs/`, `research/` or Codex's files was modified.** The original SSE workbook in `~/Downloads` was only read: SHA-256 `3be1ead9…f051f0`, unchanged before and after.

## 1. Status in one paragraph

A working end-to-end MVP runs locally against a **labelled dev mock API** that speaks Codex's contract. The flow covers phone capture, workbook onboarding with baseline exceptions, inbox, review with the cell-level Excel diff, hash-bound approval, versions and downloads, the live execution monitor, and the containment test. Only the two Vultr Serverless Inference calls are mocked (receipt extraction and code generation). The rest is real: accounting rules, T-account mapping, slot allocation, OOXML cell writes, a hardened Docker sandbox, the independent verifier, approval, versions, SSE and idempotency. The UI is integration-ready: it uses `/api/v1` only and stays on contract paths and shapes, except for the extensions listed in §5.

**Integration is now a configuration step, not a project:**
- **Real Vultr inference is wired and tested.** Set `VULTR_INFERENCE_API_KEY` and `LEDGERFLOW_VSI_MODEL` and the mock switches from fixtures/template to real extraction (call 1), account proposal (call 2) and code generation (call 3), following Codex's structured-output ladder (`json_schema` → `json_object` → plain + one repair). Tested end to end against a local OpenAI-compatible fake (§2).
- **Codex's backend can be validated in one command** (`frontend/contract/check_backend.py`, §3b): 34 contract checks over the UI's real flow. It passes against the mock today.

## 2. What was verified tonight (real runs, not claims)

| Check | Result |
|---|---|
| `accounting/tests` (pytest) | **30 passed**. Real SSE facts reproduced: 32 accounts, 369 slots, gap 87,976.00, cause G48/B76, E1 lands on exactly K64/L64/K38/L38/R12/S12/R13/S13. Negative cases B-21…B-26 rejected (openpyxl save, formula edit, OB write, ref-as-number, half posting, balanced phantom payable). |
| `frontend/dev-mock-api/test_mock_api.py` | **4 passed** with **real Docker sandbox runs**: full flow (E1 → approve → commit → idempotent replay → SSE order → duplicate refused); review → correction → approve; stale base → re-run → approve; injection held + 4-probe containment; corrections only touch changed fields. |
| `frontend/dev-mock-api/test_vsi_integration.py` | **1 passed**: real-inference path against a local fake of `api.vultrinference.com/v1`. `json_schema` rejected (HTTP 400) → `json_object` fallback; a non-fixture receipt becomes the correct entry 6110/2640/1940; account proposal 6110; the first generated program (`import socket`) is **refused by the static screen before execution**, the refusal goes back to the model as a repair hint, and attempt 2 runs in Docker, verifies and is approved; the API key never appears in anything sent to the sandbox. |
| `frontend/contract/check_backend.py` vs the mock | **34/34 PASS** (auth, onboarding, upload, run, SSE replay/order/fields, diff with the 12 mandatory checks, employee 403, tampered-hash 409, commit, versions) |
| `npm test` (Vitest) + `tsc --noEmit` + `vite build` | 4 passed; typecheck clean; build 284 KB JS (88 KB gzip). |
| Browser pass (built-in browser, phone and desktop widths) | Onboarding (error workbook → "out by SEK 1,600.00, L74/Q74"), confirm mapping, phone capture, review, monitor, approve, containment, B11 correction, B27 security hold, stale → re-run, versions v1–v4. |
| Excel (Microsoft Excel for Mac via AppleScript, alerts on) | Synthetic workbook, its patched candidate, and the final committed v4 all open **without a repair dialog**; dropdowns intact; v4 shows the three posted lines. |
| Accounting of the committed v4 | +2,062.50 debit and +2,062.50 credit (1,250 + 375 + 437.50); pre-existing 1,600.00 gap unchanged; 0 new unreconciled lines. |

Bugs found and fixed while testing (Docker Desktop also needed one clean restart after it returned HTTP 500 to API calls): settlement side rule (V-SEM-01); UTC vs Europe/Stockholm "future date" false review; ambiguous money parsing ("1,250", "12.345" now refused); correction form overwriting document evidence; panel layout; phone navigation.

## 3. How to run (2 commands)

```bash
cd ~/Coding/vultr/frontend && npm ci && npm run build
```

```bash
cd ~/Coding/vultr && LEDGERFLOW_SANDBOX_IMAGE=python:3.12-slim python3 frontend/dev-mock-api/server.py
```

Then open http://localhost:8787 and sign in with `owner-demo`, then `employee-demo` / `accountant-demo`. Tonight the sandbox image was `automotive-diagnostic-ai-backend:latest`, a Python 3.12 image already on this Mac. `python:3.12-slim` was **not pulled** (no downloads without approval): run `docker pull python:3.12-slim` once. Regenerate fixtures any time with `python3 fixtures/build_fixtures.py`.

## 3a. Strict-contract mode

`LEDGERFLOW_STRICT_CONTRACT=1` makes the mock strip every proposed extension (§5). With it, the conformance checker still passes 34/34, and the UI works with no console errors. Downloads fall back to the Versions page. So the UI works against a backend that implements only the written contract.

## 3b. Validate Codex's backend the minute it runs

```bash
python3 frontend/contract/check_backend.py --base https://<backend> --owner-invite <tok> --accountant-invite <tok> --employee-invite <tok> --workbook fixtures/synthetic/nordvik_t_accounts.xlsx --receipt fixtures/synthetic/receipts/E1.png
```

It prints PASS/FAIL per step with the exact missing field names, and uses no mock-only route. `--no-approve` stops before committing.

## 3c. Switch the mock to real Vultr inference (when credentials arrive)

```bash
VULTR_INFERENCE_API_KEY=<key> LEDGERFLOW_VSI_MODEL=<model id from the hour-1 spike> LEDGERFLOW_SANDBOX_IMAGE=python:3.12-slim python3 frontend/dev-mock-api/server.py
```

The banner, the session (`inference: "vultr"`), run labels and events then say so; events carry `model_id`, `mode` and token `usage`. Catalog vision candidates (from Codex's `research/vultr-models-2026-11-26.json`): `qwen3.8-27b`, `qwen3.8-flash-next`, `glm-5.3-flash`, `deepseek-v4.1-flash-1017`, `mimo-v2.6-flash`, `minimax-m3.1-flash`. **Untested with real credentials.** Codex can lift `vsi.py` and `codescreen.py` into the orchestrator unchanged.

## 3g. Design: "The Ledger Grid" identity (27 Nov, afternoon). For Codex and the design team

Direction chosen by the user on the impeccable decision page: the cell is the brand. One device everywhere: a selection rectangle with a square fill handle (logo, active nav, focus, the newest row, the shutter). Unverified values are grey; verified values print black. Contract: `.impeccable/surfaces/frontend-src-app-tsx.md`.

- **Identity.** `frontend/src/Brand.tsx` (LF monogram as a selected cell; the outlined wordmark is kept). `native/assets/generate_identity.py` redraws the web, iOS and Mac icons (`python3 native/assets/generate_identity.py && python3 native/ios/scripts/generate_assets.py`). Tokens and motion live in `frontend/src/grid.css`, loaded last, so the older sheets keep working underneath. Fonts are self-hosted: Schibsted Grotesk for display, Martian Mono for cell addresses and amounts only.
- **Phone home.** `frontend/src/pages/Home.tsx` (`#/home`) has a live mini-sheet of real runs, the shutter and "How it works". Owners on the phone (LOCAL) get a Home tab.
- **How it works.** `frontend/src/Explainer.tsx` (`#/how`): four animated scenes, swipe and arrow keys, pause, reduced motion, "sample figures" label. It opens once on a phone's first launch (`localStorage ledgerflow.howSeen`), and from Home or the agent welcome on the Mac.
- **Languages EN/FR/SV.** `frontend/src/lib/i18n.ts` covers the shell, nav, home, explainer and agent UI. The switch sits in the toolbar. Review, capture and settings pages are still mostly English: extend the dictionary there. The agent answers in the language of the user's message (`native/desktop/assistant.py`, `language` sent by `Agent.tsx`).
- **Mac motion.** Page rise, list stagger, the selected transaction lifts while the rest dims, diff cells write themselves in, the sidebar's active item is the selected cell.
- **Native iOS.** The first screen, before pairing, is now `WelcomeView` in `native/ios/LedgerFlow/LedgerFlowApp.swift`: an animated grid story (four steps), "Pair with my Mac", and the paste-link and other options. Texts follow the iPhone language (EN/FR/SV). Built and run in the iPhone 18 Pro simulator with Xcode-beta (`DEVELOPER_DIR=~/Downloads/Xcode-beta.app/Contents/Developer`); the launch colour is updated. Not run on a physical iPhone.
- **Landing.** `landing/` is a static page (no build): the EN/FR/SV switch, a live hero sheet, a scroll-driven "how it works", a proof table from real measurements, the security log, and the Mac download pointing to `github.com/asnd/ledgerflow/releases/latest`. Mac App Store and App Store are marked "planned". The repo `asnd/ledgerflow` was not reachable from here (private or a wrong URL): copy `landing/` into it.
- **Tests touched.** `frontend/e2e/web-smoke.mjs` now expects the explainer on the phone's first launch, then the new home: 12/12 PASS against the DEV MOCK API. It again writes its screenshots to `artifacts/apple-platform/`. 18 frontend unit tests (including i18n completeness) and the typecheck pass. The backup of every replaced file is in `.impeccable/backup/`.

## 3f. Final release pass (27 Nov, 14:30 CET): remaining integration dependencies

Intelligence engine frozen: `qwen3.8-27b`, `reasoning_effort=minimal`, codegen prompt v2, accounting rules and verifier
unchanged. The only rule change is a **non-blocking approver warning above SEK 4,000** (check buyer name, address and seller
VAT number), required by the Kvittion spec; entries are unchanged. Demo package: `demo/` (README inside). Jury evidence:
`DEMO_EVIDENCE.md`; stage script: `DEMO_SCRIPT.md`; release status: `FINAL_RELEASE_CHECKLIST.md`.

| Dependency | Needed for | Owner | How to verify when ready |
|---|---|---|---|
| Public HTTPS deployment on Vultr (app + API + TLS) | "Public Vultr deployment" claim, phone capture over HTTPS | Infrastructure lead | `python3 demo/final_suite.py --base https://HOST --owner-invite … --accountant-invite … --employee-invite …` |
| Sandbox runtime on the Vultr VM (gVisor) measured | "Sandbox on Vultr infrastructure" claim | Infrastructure lead | `DEPLOYMENT.md` §8 + `benchmark/security_evidence.py` |
| Production backend with runs, approval and commit (today: health routes only) | Retiring the DEV MOCK API; dev routes off in production | Codex | `frontend/contract/check_backend.py` ALL PASS, then the final suite with `--base` |
| Same prompts in the production backend | Measured behaviour carries over | Codex | Hash your prompts against `config/inference.json` |
| Real iPhone capture test | Phone story on stage | Codex + team | Photograph `demo/receipts/1_success_receipt.pdf` (printed) with the phone |
| `web-smoke.mjs` writes a hard-coded `inference: MOCK_INFERENCE / MOCK_CODEGEN_TEMPLATE` label into `artifacts/apple-platform/browser-test-results.json`, even when the backend runs live | Accurate evidence | Codex | Read `session.inference` instead. My live UI run is recorded separately in `demo/out/ui_live_browser_test.json` (and it overwrote the screenshots and results in `artifacts/apple-platform/` with that run's) |

## 3e. Primary model, prompts and final live run (27 Nov, afternoon) — for Codex

- **Single source of truth:** `config/inference.json`: `qwen3.8-27b`, `reasoning_effort=minimal`, temperature 0, `max_tokens` 4000, timeout 45 s, structured-output ladder json_schema -> json_object -> plain, 1 schema repair, 2 code attempts, manual fallback `mimo-v2.6-flash@minimal`. It also publishes the SHA-256 of the three system prompts; `vsi.py` reads its defaults from it and `test_inference_config.py` fails if a prompt drifts.
- **Codex's backend must send exactly these prompts**, including codegen prompt **v2** (`CODEGEN_SYSTEM` in `frontend/dev-mock-api/vsi.py`: blank cells are absent from `cells()`). Lift `vsi.py` unchanged or hash your copies against `config/inference.json`. As of 13:00 `backend/` has only health routes, so the integrated application is the frontend + DEV MOCK API.
- **Live demo:** key in the git-ignored `.env`, then `python3 frontend/dev-mock-api/server.py --dotenv`; the start line shows `inference: Vultr qwen3.8-27b (reasoning_effort=minimal, codegen prompt v2-blank-cells-documented)`. Docker Desktop on this Mac sometimes needs a second full quit/reopen before `docker info` answers (seen 3 times today): start it well before the demo.
- **Final end-to-end run** (`python3 benchmark/e2e_live.py --excel`, results in `benchmark/results/e2e_live.json`): 7/7 receipts as expected (4 committed, duplicate / injection / Swish held), every reading and program from `qwen3.8-27b`, all programs passed first try in Docker, final workbook balanced (+8,209.00 SEK each side, gap 0 -> 0, 40/40 validation ranges), Excel opened a copy and read the written cells back.
- **KPIs for the UI:** `GET /api/v1/benchmark/kpis` (schema `ledgerflow.kpis.v1`, `benchmark/results/kpis.json`, built by `python3 benchmark/kpis.py`), typed as `BenchmarkKpis` with `getBenchmarkKpis()` in the frontend. Each KPI carries `source_kind`, sample size and an explicit `limitation`; no UI was added.

## 3d. Agent benchmark (QA, 27 Nov late morning)

`python3 benchmark/bench.py` (about 80 s, needs Docker) writes `benchmark/results/benchmark_results.json` (schema `ledgerflow.benchmark.v1`, a `headline` list ready for UI cards) and `BENCHMARK_RESULTS.md`. Every number carries a `source_kind` (deterministic, sandbox, scripted_model, mock, live_vultr, not_run); no live Vultr number exists yet. With a key: `VULTR_INFERENCE_API_KEY=<key> python3 benchmark/bench.py --live --models glm-5.3-flash,qwen3.8-flash-next,...` runs the same 22 receipts and 6 code plans through each model and fills the comparison (accuracy, hallucinations, injection detection, code first-try and after-repair, latency, tokens, USD from catalog prices).

The baseline run found 8 real defects; 7 are fixed and re-measured (`benchmark/results/benchmark_results.baseline.json` keeps the before state):
- unpaid supplier invoices went to review because `vsi.to_transaction` demanded a paying account (now only for paid documents);
- duplicates were only caught against committed runs with byte-equal names and references: now pending runs count, names/references are normalised, same file bytes match, and receipts with no number fall back to supplier + date + total (`server.semantic_duplicate`, Codex should port the rule);
- the verifier crashed on a package missing a listed sheet; `Workbook()` now refuses it (`archive_safe` fails).

**Live Vultr results (27 Nov, real calls, see `BENCHMARK_RESULTS.md` "Live Vultr model comparison"):** 18 configurations (9 vision models x model-default / minimal reasoning) on the same 22 receipts and 11 code plans, then the 8 viable ones again with codegen prompt v2. Computed spend: 1.57 + 0.38 USD. Measured recommendation for the app (one model for all three calls): `LEDGERFLOW_VSI_MODEL=qwen3.8-27b LEDGERFLOW_VSI_REASONING_EFFORT=minimal` (22/22 receipts booked right, 0 invented critical facts, 3/3 injections flagged, 11/11 programs passed first try, about 0.004 USD and 6 s per receipt). Budget alternative within one receipt: `mimo-v2.6-flash@minimal` (5x cheaper). Model-default reasoning is not usable with `max_tokens` 4000 and a 45 s timeout: reasoning tokens exhaust the budget (up to 15/22 failed calls). The benchmark also found and fixed a codegen prompt gap (blank cells are absent from `cells()`), which raised first-try code success from 9-46 % to 64-100 % on most models.

**Live Vultr run (for Codex, credentials and model choice):** the harness reads `VULTR_INFERENCE_API_KEY` from the environment or the macOS Keychain (service `ledgerflow-vultr-inference`), never from a file, and redacts it from outputs as a last guard. It measures every vision model of the live catalog by default (prices from the catalog itself) and writes a computed recommendation (`live.recommendation`, with the env to set). Codex: if your orchestrator uses another key or base URL, export them under the same names; pick the production model from that table, not from catalog claims.

**Update 27 Nov 13:00:** the infrastructure lead's new `sandbox.py` was re-measured with the full local suites: 13/13 containment probes contained, P13 closed (write stops with ENOSPC at 128 MiB). One regression found (output lost on deadline kill); fixed by the infrastructure lead at 13:04 and re-checked (output kept, `test_mock_api.py` green). Earlier note, now resolved: `/work` is a host bind mount with no size limit; a sandboxed program wrote 256 MB unopposed (P13). Give each run a size-capped scratch (tmpfs-backed volume or a quota'd filesystem on the VM) and re-run the suite there.

## 4. What is where

| Path | Content |
|---|---|
| `frontend/src/` | `App.tsx` (shell, hash routes, mock banner), `pages/` (Login, Capture, Onboarding, Inbox, Review, Versions, Security), `lib/api.ts` (typed client), `lib/types.ts` (contract types), `lib/format.ts` (öre money, approval tuple, SSE merge), `styles.css`, `ui.tsx` (authored SVG icons, pills, callouts) |
| `frontend/dev-mock-api/` | `server.py` (**DEV MOCK**, stdlib HTTP + SSE), `sandbox.py` (hardened `docker run`), `vsi.py` (real Vultr Serverless Inference adapter, env-switched), `codescreen.py` (static screen of generated code, V-SEC-02), `programs.py` (mock codegen template + containment probe), tests |
| `frontend/contract/check_backend.py` | Contract conformance checker for any backend |
| `accounting/ledgerflow_accounting/` | Stdlib-only package Codex can import: `admit` (TransactionV1 → EntryV1 or named review reasons), `checks` (balanced-but-wrong checks V-SEM-*), `tacc` (T-account detection from the workbook's own validations, trial balance, contra reconciliation, deterministic slot allocation → CellOperationV1/PostingAllocationV1), `verify` (reference independent verifier emitting Codex's 12 mandatory check IDs), `reference_writer` (test/mock writer; production writer is Codex's helper) |
| `fixtures/synthetic/` | `nordvik_t_accounts.xlsx` (authored from scratch, publishable), `_error.xlsx` (wrong-side posting), `receipts/*.png` (E1, E2, B11, B12, B27), `cases.json` (ground-truth TransactionV1 + expected entries). A nested `.gitignore` re-includes `*.xlsx`/`*.png`, which the root ignores |
| `fixtures/private/` | `sse_anonymized.xlsx` (git-ignored; name/ID/path removed; generator refuses if PII remains) |
| `fixtures/build_fixtures.py` | Deterministic generator for all of the above |

## 5. Contract alignment: differences to resolve with Codex at 09:00 (none silently decided)

| # | Item | What the UI/mock does | Proposal |
|---|---|---|---|
| C1 | `TransactionV1` has no seller org/VAT number | `supplier_org_no` field; admission requires it to deduct VAT (Skatteverket invoice rules) | Add `supplier_org_no` (nullable) to TransactionV1 |
| C2 | `RunSnapshotV1` has only `state_reason` | Extra `review_items[]`, `advisories[]`, `security_flags[]`, `duplicate_of`, `code_artifact_id`, `mock_labels[]`, `approval_expires_at` | Add `review_items` at least: the UI asks precise questions from it |
| C3 | `GET /runs/{id}/diff` shape unspecified | `{validation: ValidationReportV1, operations, base_version_id, base_sha256, candidate_sha256, plan_sha256, mapping_sha256, policy_version}`. The UI builds ApprovalRequestV1 only from this response | Adopt this shape |
| C4 | `CommitV1` has no download ids | `artifact_id`, `audit_artifact_id` | Add both (or a link in the snapshot) |
| C5 | STALE_BASE is terminal | `POST /runs/{id}/rerun` creates a fresh linked run; after a commit the mock proactively marks other awaiting runs STALE_BASE | Add the route (contract already says "create a fresh linked run") |
| C6 | Containment demo has no endpoint | `POST /containment-tests`, `GET /containment-tests/{id}` (accountant/owner) | Add, or keep as a separate demo page backed by the supervisor |
| C7 | Corrections payload | `corrections` object of TransactionV1 fields + `tax_rate_basis_points` + `acknowledge_security_flag` | Confirm field list and the security-ack mechanism |
| C8 | Supplier payment (settlement, demo E3) | `admit_settlement()` implemented and tested in `accounting/`, **not** wired: `kind` only allows receipt/invoice | Decide at 09:00: add `supplier_payment` kind or drop E3 from the live demo |
| C9 | Session cookie | Mock uses `ledgerflow_session` over http://localhost; contract `__Host-ledgerflow_session` needs HTTPS | Production as contract; nothing changes in the UI |
| C10 | Session extras | `display_name`, `backend` ("DEV-MOCK") | Optional; `backend` drives the mock banner only |
| C11 | ValidationReport extras | `not_passed_mandatory[]`, `runtime` | Optional |
| C12 | Mock-only routes | `/dev/fixtures*` (sample files) | Never in production |

The UI uses these ValidationReportV1 fields: `result`, `report_sha256`, `verifier_version`, `checks[{check_id,status,detail}]`, `cell_diff[{sheet,cell,after,account_id,side,amount_delta_minor,line_id,allocation_id,reason}]` with `reason` = operation role (`debit_reference`…), `account_deltas`, `baseline.difference_minor`, `limitations`.

## 6. Mocked vs real (also shown in the UI banner and per run)

- **MOCK_INFERENCE (extraction):** fixture receipts are recognised by SHA-256 and their ground truth is loaded. Any other photo goes to NEEDS_REVIEW with all fields unknown, and the reviewer types them (the correction form). Replace with VSI call 1 (`product/PROMPTS.md`).
- **MOCK_CODEGEN_TEMPLATE (code generation):** a fixed program (inspect → write via helper → self-check → export) runs in the sandbox. Replace with VSI call 3. The verifier and approval need no change.
- **Real:** everything else, including the Docker sandbox (`--network none --read-only --cpus 1 --memory 512m --pids-limit 128 --cap-drop ALL --security-opt no-new-privileges --user 10001`, 30 s, destroyed per run).

## 7. Blockers and open items (honest)

| Priority | Item | Owner |
|---|---|---|
| P0 | No Vultr credentials: the real-inference path is wired and tested against a fake, but not against the live endpoint; model choice and prompt quality are unmeasured | Team at 09:00: set the key, run one receipt, pick the model |
| P0 | Codex backend does not exist yet; mock routes and shapes are the de facto contract until it does (§5). When it exists, run `check_backend.py` against it (§3b) | Codex |
| P0 | Pre-event coding permission still unconfirmed with organisers; this code was written on the user's instruction "assuming pre-event development is authorized" | Founder at 09:00 |
| P0 | Sandbox tested on Docker Desktop (macOS), not yet on the Vultr VM (Linux). Re-run `test_mock_api.py` there | Codex |
| P0 | Public URL/TLS not set up; the cookie needs HTTPS in production | Codex |
| P1 | E3 settlement not wired (C8) | Decide at 09:00 |
| P1 | HEIC from iPhone: the picker asks for JPEG/PNG; iOS usually converts camera captures, not verified on a device | Test on a phone |
| P1 | Real-phone test over the public URL (camera capture path) | Team |
| P1 | Peak memory "not reported" (no `docker stats` sampling) | Codex |
| P2 | Layout B (journal table), mapping minimap, versions compare view | Later |

## 8. Side effects on this Mac (for transparency)

- Docker Desktop was started for the tests. Starting it also auto-started three containers from the separate `automotive-diagnostic-ai` project (their restart policy). Docker Desktop was quit again at the end to restore the earlier state.
- 27 Nov, benchmark: Docker Desktop was started again (same side effect on the `automotive-diagnostic-ai` containers) and the official `python:3.12-slim` image was pulled again (it was missing from the local cache). Benchmark probes ran only inside throwaway containers; the disk-fill probe wrote 256 MB to a temporary folder that was deleted with the run.
- Microsoft Excel was opened and closed via AppleScript only to check that files open without repair (scratch copies, closed without saving).
- npm installed exact-pinned packages: react/react-dom 19.3.1, vite 7.3.8, @vitejs/plugin-react 5.2.0, typescript 5.9.3, vitest 3.2.7, @types/react 19.3.3, @types/react-dom 19.3.0. npm skipped esbuild's postinstall script (allow-scripts policy); the build works without it.
