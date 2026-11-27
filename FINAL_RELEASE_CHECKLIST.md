# LedgerFlow final release checklist

Original QA pass on 27 November 2026, about 14:30 CET. Vultr Cloud Compute verification was added the same evening.
Status values: **VERIFIED** (evidence below), **PARTIAL**, **NOT VERIFIED** (not tested, no evidence), **NOT MET** (tested or inspected, and missing).

| # | Item | Status | Evidence / what is missing | Owner of the gap |
|---|---|---|---|---|
| 1 | Public HTTPS application | **VERIFIED** | [Jury demo](https://70.34.203.216.sslip.io/welcome/) on Vultr Cloud Compute in Stockholm. [HTTPS response](demo/vultr_evidence/https.txt) | — |
| 2 | Real Vultr Serverless Inference | **VERIFIED** (local backend) | `qwen3.8-27b`, `reasoning_effort=minimal`, codegen prompt v2: `demo/out/final_suite_2026-11-27T131821Z.json` steps 2 and 4, `benchmark/results/e2e_live.json`, `demo/out/ui_live_browser_test.json` | — |
| 3 | Sandbox execution on Vultr infrastructure | **VERIFIED** | [VM runtime](demo/vultr_evidence/host.txt) and [on-VM containment probe](demo/vultr_evidence/containment.txt) using Docker and gVisor `runsc` | — |
| 4 | Android browser receipt workflow | **VERIFIED** in emulation | [Pixel 7 browser profile](demo/vultr_evidence/jury-android.txt) over HTTPS. Sample receipt processed and downloaded, and simulated camera capture passed. Physical device testing remains pending | — |
| 5 | Accounting approval and commit | **VERIFIED** | Final suite steps 7–8 (hash-bound approval, tampered hash → 409, committed bytes = approved candidate); browser UI 12/12 including **Approve and write N cells** → Committed | — |
| 6 | Excel download and readability | **VERIFIED**, with a caveat | `.xlsx` downloaded through the UI (`ui_live_browser_test.json`). Microsoft Excel opened the committed file and read the cells back in `e2e_live.json` (12:40 UTC). In the 13:18 suite the Excel step was **not run**: macOS was waiting for a file-access click | Presenter: click "Grant Access" once when rehearsing |
| 7 | Duplicate detection | **VERIFIED** | 6/6, 0/4 false positives (deterministic); live: e2e S5 and final-suite step 11 → `DUPLICATE_REVIEW` | — |
| 8 | Security containment | **VERIFIED** | The 13/13 benchmark ran on local Docker. The [Vultr probe](demo/vultr_evidence/containment.txt) independently confirmed read-only mounts, blocked network and writes, absence of credentials, deadline enforcement, and container removal | — |
| 9 | API credentials protected | **VERIFIED** for the demo | The infrastructure key stays local. The inference key is shipped separately over SSH and stored in a root-owned `0600` environment file. The on-VM probe confirmed the key was absent from the sandbox | — |
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
| `bash infra/opentofu/verify-demo.sh` against Vultr | HTTPS 200, on-VM containment, [desktop 10/10](demo/vultr_evidence/jury-desktop.txt) and [Android emulation 10/10](demo/vultr_evidence/jury-android.txt) |
| Python: `accounting/tests`, `benchmark`, `frontend/dev-mock-api` | 59 passed |
| Frontend: typecheck, 15 unit tests, production build | passed |
| Codex backend scaffold (`.venv`, `tests/`) | 10 passed, 18 skipped |

## Critical blockers for the claims, not for the local demo

1. **Production backend (items 10 and 13).** The public jury app uses the DEV MOCK API, real inference and the real sandbox in a shared synthetic workspace.

## Re-run once a public deployment exists

```bash
python3 demo/final_suite.py --base https://HOST --owner-invite OWNER --accountant-invite ACCOUNTANT --employee-invite EMPLOYEE
```

The suite fails (exit 1) if inference is mocked or the runtime is not Docker. On the VM, also run `DEPLOYMENT.md` §8 and
`benchmark/security_evidence.py`.
