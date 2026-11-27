# LedgerFlow final release checklist

Checked 27 November 2026, about 14:30 CET, by the Final QA / Release Manager pass. Only evidence in this repository counts.
Status values: **VERIFIED** (evidence below), **PARTIAL**, **NOT VERIFIED** (not tested, no evidence), **NOT MET** (tested or inspected, and missing).

| # | Item | Status | Evidence / what is missing | Owner of the gap |
|---|---|---|---|---|
| 1 | Public HTTPS application | **NOT MET** | `DEPLOYMENT.md`: the OpenTofu stack prepares an execution host only (no app, DNS or TLS). Provisioning on Vultr not established; no public URL in any handoff | Infrastructure lead |
| 2 | Real Vultr Serverless Inference | **VERIFIED** (local backend) | `qwen3.8-27b`, `reasoning_effort=minimal`, codegen prompt v2: `demo/out/final_suite_2026-11-27T131821Z.json` steps 2 and 4, `benchmark/results/e2e_live.json`, `demo/out/ui_live_browser_test.json` | — |
| 3 | Sandbox execution on Vultr infrastructure | **NOT VERIFIED** | All sandbox evidence is local Docker Desktop (macOS). The VM gate in `DEPLOYMENT.md` §8 (runtime tests and containment on the VM) has not been run | Infrastructure lead |
| 4 | Receipt upload from a smartphone | **NOT VERIFIED** on a device | Employee upload passes in headless Chrome at phone size (`ui_live_browser_test.json`, Codex's 393 px checks). No real iPhone test; the iOS project was not compiled here; phone access over LAN is plain HTTP | Codex + team, on a device |
| 5 | Accounting approval and commit | **VERIFIED** | Final suite steps 7–8 (hash-bound approval, tampered hash → 409, committed bytes = approved candidate); browser UI 12/12 including **Approve and write N cells** → Committed | — |
| 6 | Excel download and readability | **VERIFIED**, with a caveat | `.xlsx` downloaded through the UI (`ui_live_browser_test.json`). Microsoft Excel opened the committed file and read the cells back in `e2e_live.json` (12:40 UTC). In the 13:18 suite the Excel step was **not run**: macOS was waiting for a file-access click | Presenter: click "Grant Access" once when rehearsing |
| 7 | Duplicate detection | **VERIFIED** | 6/6, 0/4 false positives (deterministic); live: e2e S5 and final-suite step 11 → `DUPLICATE_REVIEW` | — |
| 8 | Security containment | **VERIFIED** (local Docker) | 13/13 probes and 15/15 hostile programs contained (`BENCHMARK_RESULTS.md`); `demo/containment_demo.py` → CONTAINED; final suite step 13; injection receipt held (step 12) | Re-measure on the VM (item 3) |
| 9 | API credentials protected | **VERIFIED** locally | Key only in the git-ignored `.env` (mode 600), loaded by `--dotenv`, never printed. Results, logs and the working tree were scanned: the key appears nowhere outside `.env`. Production secret storage: N/A until item 1 | Infrastructure lead (production) |
| 10 | Development-only routes disabled in production | **NOT MET for the demo backend** | The demo runs on the DEV MOCK API, which has invite codes `*-demo`, `/dev/fixtures` and a sample picker by design (labelled DEV-MOCK in the session). Codex's production scaffold has none of these, but it has no accounting flows either | Codex (production backend) |
| 11 | No secrets or personal financial documents on GitHub | **PARTIAL** | This checkout is not a git repository, so GitHub could not be inspected. Local tree: no key, no secret patterns. The only `.xlsx`/`.pdf` outside ignored folders are fictional (`fixtures/synthetic`, `demo/`). The private anonymized course workbook stays under ignored `fixtures/private/`; the original stays in `~/Downloads`. `.gitignore` covers `.env`, `private/`, `artifacts/` | Whoever pushes: run `git status` and a secret scan before pushing |
| 12 | Benchmark KPI accuracy | **VERIFIED** | `benchmark/results/kpis.json` is regenerated bit-for-bit from `benchmark_results.json` and `e2e_live.json` (source SHA-256 matches); every KPI carries a source kind, a sample size and a limitation | — |
| 13 | Frontend/backend contract compatibility | **VERIFIED against the DEV MOCK API**; **NOT MET against Codex's backend** | `frontend/contract/check_backend.py` → ALL PASS against the DEV MOCK API (14:28 CET). Browser UI 12/12 against the live backend. Codex's backend: health routes only (its own 10 tests pass, 18 skipped) | Codex |
| 14 | Submission documentation | **VERIFIED** present | `DEMO_EVIDENCE.md`, `DEMO_SCRIPT.md`, this checklist, `demo/README.md`, `BENCHMARK_RESULTS.md`, `FRONTEND_HANDOFF.md` | — |

## Test runs behind this checklist (27 Nov)

| Suite | Result |
|---|---|
| `python3 demo/final_suite.py --spawn` (live Vultr, local Docker, demo assets) | 16/17 passed, 0 failed, 1 not run (Excel, see item 6) |
| `node frontend/e2e/web-smoke.mjs` with `LEDGERFLOW_REQUIRE_COMMIT=1` against the live backend | 12/12 (first attempt failed at the commit wait, cause not established; the rerun on a fresh backend passed) |
| `python3 benchmark/e2e_live.py --excel` | 7/7 as expected (4 committed, 3 held), Excel read-back OK |
| `python3 demo/containment_demo.py` | CONTAINED |
| Python: `accounting/tests`, `benchmark`, `frontend/dev-mock-api` | 59 passed |
| Frontend: typecheck, 15 unit tests, production build | passed |
| Codex backend scaffold (`.venv`, `tests/`) | 10 passed, 18 skipped |

## Critical blockers for the claims, not for the local demo

1. **No public deployment (items 1 and 3).** Do not say "deployed on Vultr" or "sandbox on Vultr infrastructure". Say "inference on Vultr Serverless Inference; sandbox demonstrated locally; Vultr VM stack prepared".
2. **No production backend (items 10 and 13).** The working application is the browser app on the DEV MOCK API, which uses real inference and the real sandbox. Say so if asked.

## Re-run once a public deployment exists

```bash
python3 demo/final_suite.py --base https://HOST --owner-invite OWNER --accountant-invite ACCOUNTANT --employee-invite EMPLOYEE
```

The suite fails (exit 1) if inference is mocked or the runtime is not Docker. On the VM, also run `DEPLOYMENT.md` §8 and
`benchmark/security_evidence.py`.
