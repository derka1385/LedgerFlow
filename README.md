# LedgerFlow — hackathon technical handoff

Your employees take pictures. Your AI does the bookkeeping. Your company keeps its Excel files.

This repository currently contains **research and implementation specifications**, not a working application. Preparation deadline: **27 November 2026, 08:00 Europe/Stockholm (07:00 UTC)**. Work may finish earlier. No work is to continue beyond that cutoff.

Public event material did not explicitly authorize pre-event development. The user's brief makes that permission a prerequisite for application code, Docker configuration, deployment scripts, synthetic fixtures, and automated application tests. Those are specified here for implementation during the event. No VM has been provisioned, no authenticated inference request has been made, and no sandbox or application test has been run.

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
