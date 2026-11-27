# LedgerFlow master plan

Prepared 26 November 2026 for the Vultr Agent Runtime Hackathon, Stockholm, 27 November. Hard preparation stop: **08:00 CET on 27 November**. All event times below use Europe/Stockholm.

## Product and winning demonstration

LedgerFlow adapts a bounded set of existing Excel accounting layouts, proposes evidenced journal entries, generates Python, runs it on Vultr, independently checks the resulting workbook, and commits only the artifact a person approved. The visible product is a financial execution workflow with receipts, logs, cell changes, and a reversible version history.

Demonstrate one paid office-supplies receipt against the inspected T-account workbook and one conventional journal layout. Onboarding identifies accounts and write slots rather than choosing a bundled template. Explain the support boundary explicitly: preformatted T-account blocks and journal ranges in ordinary `.xlsx` packages, subject to a compatibility scan. Unsupported structures enter manual mapping or a clear refusal.

The strongest evidence is a real modified workbook, generated code, independently derived cell diff, hash-bound approval, and actual containment logs. A polished receipt extraction screen alone does not meet this objective.

## Eligibility and preparation constraint

The [event page](https://community.vultr.com/e/vultr-agent-runtime-hackathon) and [registration page](https://luma.com/stockholm-nn3n) were inspected. They do not explicitly establish permission for pre-event implementation. Consequently this handoff contains specifications and source research. It does not contain application code, runnable infrastructure configuration, fixtures, or application test implementations. At registration, ask whether preparation documents, generated specifications and any prebuilt code are allowed, and disclose this preparation honestly. Do not infer permission from silence.

Public agenda: registration 09:00, welcome 09:30, hacking 10:00, submission 19:00, doors close 21:00. The community agenda labels its times UTC and has some inconsistent late-day items; use 19:00 as the conservative submission cutoff and confirm onsite. A 12-hour event is approximately nine hours of implementation before submission, not twelve build hours. [Registration agenda](https://luma.com/stockholm-nn3n)

## P0: required path, in priority order

| Order | Deliverable | Acceptance condition | Cut if late |
|---|---|---|---|
| 1 | Public Vultr application + VSI access | HTTPS page reachable on phone; authenticated model request recorded | All visual embellishment |
| 2 | Real sandbox boundary | Generated Python runs outside backend process; hard timeout and cleanup proven | Alternate sandbox frameworks |
| 3 | Package scan + workbook mapping | Actual account regions and instructions loaded; mapping confirmed once | Automatic remapping of complex workbooks |
| 4 | Deterministic accounting and verifier | Exact minor-unit balance; output deltas match plan; forbidden cells unchanged | General accounting categories |
| 5 | Approval + immutable version commit | Wrong hash/stale base refused; approved bytes downloadable | Multi-user collaboration features |
| 6 | Receipt vision + planning/code generation | Actual photo → VSI extraction → plan/Python → sandbox output | PDF and HEIC ingestion |
| 7 | Live run evidence + containment | Logs show unsafe file read blocked and loop terminated; app healthy | Animated logs and charts |
| 8 | Second layout | Journal adapter passes same plan/verifier protocol | Advanced Excel Table growth |
| 9 | Submission | Public repo, URL, recorded video, architecture, evidence complete | Any new feature |

Orders 1–5 can use a manually entered transaction **during development**. The submitted core flow requires actual VSI reasoning and generated code. Manual entry is a transparent input correction path, never a disguised vision result.

## P1 only after P0 passes

One bounded model repair from a real ordinary execution error, QR pairing, richer account mapping review, formula-cache warnings in workbook preview, and a second photographed receipt. Mapping correction UI with row/column selectors is more valuable than more models.

## Do not build at this event

Bank integrations, payment initiation, payroll processing, tax filing, foreign exchange, legal VAT determination, employee reimbursement, OCR training, mobile native apps, Kubernetes, a vector database, a general-purpose agent framework, arbitrary package installation, universal Excel support, real-time Excel coauthoring, full formula evaluation, or a bespoke VM scheduler. Do not add Gmail/Drive integrations merely to make the workflow appear larger.

## Explicit assumptions and boundaries

* Demo currency SEK, exponent 2. API money uses integer minor units. Source workbook displays whole SEK; this does not authorize rounding away öre.
* Expense category, tax treatment and payment method are confirmed inputs. An image saying “card” cannot establish which bank account or whether an employee paid personally.
* Demo invoices are ordinary domestic examples with explicit amounts. VAT shown in examples is a configured demo assumption, not a rule inferred from Sweden or a supplier name.
* Existing files have no embedded transaction IDs or dates in T-account rows. The app supplies its own auditable transaction registry. It cannot retrospectively prove every legacy posting's identity.
* “Commit” means making an immutable workbook version current inside LedgerFlow and enabling download. It does not silently edit an Excel file open on a desktop or sync changes to Downloads.
* The source workbook is an accounting assignment with personal fields. Keep its binary and raw inspection private; use a newly authored, redacted demonstration workbook at the event unless the user authorizes public display of this file.
* A known baseline problem is displayed and preserved. A new balanced posting does not make a flawed historical workbook correct.

## Ship/no-ship gates

1. No inference credentials, Docker socket or host file mounts inside execution containers.
2. Required containment tests pass on the **deployed Vultr host**, with host-side evidence.
3. No candidate can enter approval until verification and sandbox cleanup both succeed.
4. Approval includes candidate, base, plan, mapping and validation hashes. No regeneration after approval.
5. A stale approval never rebases automatically. Rerun on current base and request a new approval.
6. Public anonymous access permits landing page and recorded/sanitized examples only. Real upload/run endpoints require an invited session and quotas.
7. Missing photo fields, unsupported features, missing slots, payment ambiguity or unknown tax policy stop for review.

## Requirement-to-evidence checklist

| Requirement from user brief | Build output/evidence |
|---|---|
| Vultr central orchestration | Host instance ID/region + API state transitions and deployment diagram |
| All runtime LLM reasoning via VSI | Server-side base URL allowlist + redacted request IDs/model IDs |
| Real generated code and multi-step work | Code artifact, attempt log, independent output report |
| Limits and lifecycle | Host runtime inspection, deadline result, cleanup acknowledgement |
| Adaptive Excel | Confirmed mapping from uploaded workbook + second layout run |
| Verifiable financial result | Plan, exact deltas, minor-unit checks and downloadable candidate |
| Human supervision | Approved hash tuple, actor, timestamp and committed version |
| Containment moment | Dummy-file denial and loop termination video/logs |
| GitHub, URL, video | Submission links and tagged commit recorded in evidence index |

See [TEST_PLAN](TEST_PLAN.md) for precise acceptance cases and [HACKATHON_EXECUTION](HACKATHON_EXECUTION.md) for owner/time allocation.
