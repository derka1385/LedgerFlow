# LedgerFlow

**Snap the receipt. It's in your Excel.**
An accounting agent for small businesses: photograph a receipt and LedgerFlow books it in the Excel workbook you already use, after you approve.

### 🧪 Jury: [try the live web app — no account](https://smilies-hoping-derived-delivering.trycloudflare.com/welcome/)

Opens the real LedgerFlow app with a shared demo workspace (fictional data): connect the sample workbook, send a sample receipt, ask the agent, approve, download the modified `.xlsx`. Works in any browser (Windows, Android, Mac). If a receipt was already sent by someone else, LedgerFlow flags it as a possible duplicate: choose **Different purchase: continue**.

### 👉 [Open the landing page](https://derka1385.github.io/LedgerFlow/) · [Watch the demo film](https://derka1385.github.io/LedgerFlow/landing/#film) · [Download the demo video (MP4)](landing/assets/demo-film.mp4)

| | |
|---|---|
| **Landing page** | https://derka1385.github.io/LedgerFlow/ |
| **Demo film** | 4 min, real Mac + iPhone recordings, live Vultr inference and a real sandbox containment test |
| **Status** | Beta, built for the Vultr Agent Runtime Hackathon (Stockholm, 27 Nov 2026) |
| **Apps** | Mac app (local engine) · web agent · iPhone app (optional, pairs with the Mac over local Wi-Fi) |

## How it works, in one minute

1. **Snap it.** Photograph a receipt on the iPhone, or drop a photo/PDF on the Mac.
2. **It reads it.** Vultr Serverless Inference (qwen3.8-27b) reads supplier, date, total, VAT and payment; every value keeps the text it came from.
3. **Rules decide.** Deterministic Swedish accounting rules, not the model, build a balanced entry and the exact cells to write.
4. **A sealed box writes.** Generated Python edits the workbook inside a disposable Docker sandbox (no network, no keys, read-only input, 1 CPU, 512 MB), then the container is destroyed.
5. **You approve.** An independent verifier re-opens the real file (21 checks); your approval is bound to that file's sha256. The previous version is kept.

Measured on a synthetic benchmark (27 Nov 2026): 22/22 receipts booked right live on Vultr, 13/13 sandbox escape probes contained, 16/16 tampered workbooks rejected, about USD 0.004 of inference per receipt. Details: [BENCHMARK_RESULTS.md](BENCHMARK_RESULTS.md), [film/VERIFICATION_REPORT.md](film/VERIFICATION_REPORT.md).

**Honest limits:** in the recorded demo the backend and sandbox run on the Mac (Docker Desktop); the Vultr Cloud Compute runner is prepared with OpenTofu but not yet deployed. The Mac build is unsigned during the beta.

## Run it locally

```bash
sh demo/start_demo.sh      # needs Docker Desktop and VULTR_INFERENCE_API_KEY in .env
```
Then open http://localhost:8790 (invites: `owner-demo`, `employee-demo`). Stop and clean with `sh demo/reset_demo.sh`.

---

## Original hackathon handoff (27 Nov 2026, before the event)

## Start here at 09:00

1. Read [the master plan](docs/MASTER_PLAN.md) and [event execution plan](docs/HACKATHON_EXECUTION.md).
2. Confirm coding eligibility and submission time with organizers. Public schedules indicate hacking starts at 10:00 and submission closes at 19:00 Stockholm time.
3. Split ownership using [repository and team boundaries](docs/REPOSITORY.md).
4. Implement against [API contracts](docs/API_CONTRACT.md), [data contracts](docs/DATA_SCHEMAS.md), and [database design](docs/DATABASE.md).
5. Ship one real receipt-to-approved-XLSX path before adding breadth. Record [the containment demo](docs/DEMO.md) before the final hour.

## Documents

| Document | Purpose |
|---|---|
| [MASTER_PLAN](docs/MASTER_PLAN.md) | Priorities, acceptance gates, scope cuts |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | Trust boundaries, orchestration and commit protocol |
| [API_CONTRACT](docs/API_CONTRACT.md) | REST, SSE, idempotency, permissions |
| [AGENT_RUNTIME](docs/AGENT_RUNTIME.md) | States, prompts, retries and sandbox lifecycle |
| [EXCEL_ENGINE](docs/EXCEL_ENGINE.md) | Adaptive mapping, safe editing and independent validation |
| [SSE_WORKBOOK_AUDIT](docs/SSE_WORKBOOK_AUDIT.md) | Direct inspection of the actual Downloads workbook |
| [DATA_SCHEMAS](docs/DATA_SCHEMAS.md) | Normative field definitions and examples |
| [DATABASE](docs/DATABASE.md) | Tables, constraints, durable jobs, atomic commits |
| [SECURITY](docs/SECURITY.md) | Threat model, runtime policy, containment proof |
| [DEPLOYMENT](DEPLOYMENT.md) | Single-VM Vultr OpenTofu deployment, runtime checks, evidence export and teardown |
| [VULTR_DEPLOYMENT](docs/VULTR_DEPLOYMENT.md) | Host setup, secrets, HTTPS, release and rollback |
| [TEST_PLAN](docs/TEST_PLAN.md) | Acceptance tests and evidence requirements |
| [COST_ANALYSIS](docs/COST_ANALYSIS.md) | Verified catalog rates and estimated scenarios |
| [HACKATHON_EXECUTION](docs/HACKATHON_EXECUTION.md) | Three/four/two-person execution schedules |
| [DEMO](docs/DEMO.md) | Live script, recording and submission evidence |
| [DECISIONS](docs/DECISIONS.md) | Alternatives and explicit tradeoffs |
| [RESEARCH](docs/RESEARCH.md) | Dated primary sources and unresolved questions |
| [RED_TEAM](docs/RED_TEAM.md) | Ten likely failures and mitigation gates |
| [VERIFICATION](docs/VERIFICATION.md) | What was actually checked in this preparation |

Public catalog snapshots are in `research/`, each accompanied by URL, timestamp, HTTP status and SHA-256 provenance. Workbook inspection output stays in ignored `research/private/`. The original workbook remains in Downloads, unchanged. Do not publish it: it contains student identity fields and document metadata. Workbook-specific coordinates in the audit are technical findings, not a license to distribute the source.

A concrete [proposed mapping](docs/sse-mapping.proposed.json) and [observed baseline](docs/sse-baseline.observed.json) are included as specifications derived from the actual file. They are unconfirmed and have never been used to edit a workbook.

## Local commands

- Python: `uv sync --frozen --extra dev`, then `uv run --frozen --extra dev pytest`.
- API database: `DATABASE_URL` (PostgreSQL). Database tests need `LEDGERFLOW_TEST_DATABASE_URL` pointing at a disposable PostgreSQL database; without it they skip.
- Frontend (`frontend/`): `npm ci`, then `npm test`, `npm run build`, `npm run test:browser`, `npm run test:pwa`, `npm run package:web`, `npm run icons`.

## Current evidence status

| Claim | Status |
|---|---|
| Event requirements and agenda reviewed | Public pages read |
| Live model identifiers and published rates | Catalog GET returned HTTP 200; saved |
| VM plans and Stockholm region | Catalog GETs returned HTTP 200; saved |
| Actual SSE workbook inspected | ZIP/XML and cell-level inspection completed |
| Excel native opening/recalculation | Not performed |
| Pre-event coding allowed | Not established |
| Model vision/schema/tool reliability | Not tested |
| Sandbox containment | Test procedures specified; not executed |
| Application, deployment, public demo, video | To build during the event |
