# Event execution plan

All times are **27 November 2026, Europe/Stockholm (CET)**. Preparation ends no later than 08:00. The [registration agenda](https://luma.com/stockholm-nn3n) lists doors 09:00, welcome 09:30, coding 10:00 and submission 19:00. Confirm the exact cutoff onsite. Budget nine build hours and submit by 18:30 internally.

## Team assignments

| Person | Primary responsibility | First concrete handoff |
|---|---|---|
| A — runtime/infra lead | Vultr host/HTTPS, gVisor supervisor, hardening, containment evidence, release | Actual bounded safe job and dummy/timeout probes on Vultr |
| B — backend/agent lead | Contracts, durable state/DB, VSI client, accounting admission, approval/commit | One admitted transaction → run snapshot/events → exact version commit |
| C — frontend/product lead | Workbook mapping review, phone upload, live run/review UI, demo/video | Phone upload to deployed backend and hash-bound approval screen |
| D — Excel/verification lead | Direct package inspector, two layout adapters, safe writer, independent verifier | Candidate/diff preserving all forbidden parts and rejecting corrupted output |

Three people: A combines runtime with deployment; B combines backend and Excel but prioritizes the narrow source-cell writer and invariant checks; C owns UI, fixtures and recording. B must not spend the morning creating a general accounting framework. A helps implement verifier packaging after runtime passes.

Two people: A owns backend/runtime/infra, B owns UI/Excel. Limit to one category and one primary layout first, then add the second adapter against the shared contract. If the second layout cannot pass before freeze, disclose partial scope; do not weaken security to claim breadth. This team is at materially higher delivery risk.

## Schedule and integration gates

| Time | Parallel work | Observable gate |
|---|---|---|
| 09:00–09:30 | Confirm eligibility, team, credits, agenda and domain access; read MASTER_PLAN | Owners assigned; organizer answers recorded; no assumption of permission |
| 09:30–10:00 | Clarify policies/fixtures and interfaces only within organizer rules | Shared contracts agreed; coding starts only when allowed |
| 10:00–10:30 | A provisions host/HTTPS/runtime; B creates contracts/state/DB skeleton; C UI shell; D inspector/map | Freeze API and internal interfaces at 10:30 |
| 10:30–11:30 | A runtime limits + actual probes; B VSI smoke gates; C real upload; D cell writer/verifier on simple balanced fixture | **G1:** deployed page, actual VSI image response, real isolated Python, timeout/cleanup |
| 11:30–12:30 | B/D connect plan/admission/slots/output; C renders real run state/diff; A supervises parsing/export | **G2:** one generated program produces verifiable candidate; source unchanged |
| 12:30–13:00 | Stagger lunch, keep one integrator active; fix G2 blockers | No new features until G2 passes |
| 13:00–14:00 | B exact approval/commit/idempotency; C phone/desktop flow; D preservation negatives; A crash/reaper | **G3:** approved bytes committed once; stale/wrong hash refused |
| 14:00–15:00 | D second journal/T-account adapter; B mapping caching; C mapping review; A security negatives | **G4:** same receipt semantics across two supported layouts |
| 15:00–16:00 | Full containment + recovery demo; test actual phone; source/native Excel check; prepare repo | **G5:** actual protected-file denial, loop kill, healthy app and safe retry |
| 16:00–17:00 | Record first complete video and evidence; fix only observed failures | Working submission bundle exists before feature freeze |
| 17:00–18:00 | Freeze features, rehearse fresh-state run, redact repo/evidence, confirm links | Tagged source commit, public URL and playable video |
| 18:00–18:30 | Submit with buffer; retain a local copy and confirmation | **G6:** submission accepted/recorded |
| 18:30–19:00 | Only submission/link emergencies; no risky redeploy | Verify final entry points to intended release |

## Timebox and scope-cut rules

* gVisor install/runtime compatibility: 30 minutes initial timebox. If blocked, A follows the documented isolated runner fallback or explicitly reports incomplete runtime; no silent unconfined execution.
* Model image/schema gate: 20 minutes per candidate, at most two candidate swaps. Keep all reasoning on VSI and use strict JSON validation if schema mode is unreliable.
* Domain/DNS/certificate trouble by 11:00: obtain organizer hostname/help immediately; never wait until video time to discover the phone cannot use HTTPS.
* If G2 is not passed by 13:00, cut PDF/HEIC, QR pairing, PWA install, extra account categories, graphs and animation. Keep one clear JPEG and one receipt category.
* If preservation writer is not reliable by 14:00, demonstrate supported simple workbook writing and actual SSE read-only analysis with an explicit compatibility limit. Do not claim the SSE file was safely edited.
* If G3 fails by 15:00, stop second-layout expansion and fix artifact/approval correctness first.
* If G4 fails by 16:00, preserve the working first layout and label the second unsupported. A partial honest product beats fabricated coverage, but the original two-layout objective remains unmet.
* By 17:00, all team members stop adding features. Protect video, URL, repository and evidence deliverables.

## Thin vertical slice

First run may use manual transaction fields to prove infrastructure, actual Python and commit semantics. Then replace the input with real photo extraction and generated code before the submitted demonstration. Use visible labels for manual/development inputs. No mock response, fixed workbook download or prerecorded terminal output may be presented as the live agent.

The first category is confirmed office supplies paid from a company account with explicit configured tax treatment. Add supplier invoice liability only after this path works. Salary, refund, FX and missing-payment-context cases stay in review.

## Team coordination

Ten-minute integration checkpoint each hour: what passed, current blocker, next shared artifact. Use contracts and run IDs, not four incompatible local payload formats. The lead decides cuts; each owner records evidence for their claimed behavior. Avoid rewriting each other's directories. Contract owner approves typed payload changes immediately, and the consuming pair updates them together.

At 16:00 assign C as recording/submission owner, A as deployment owner, B as integration freeze owner and D as verifier/evidence owner. The last hour is not the time for architectural upgrades.

## Onsite questions that actually matter

Ask organizers for explicit pre-event code/preparation rules, exact submission deadline/timezone, credit scope, accepted video/link format and any judging rubric not present on the event page. Do not borrow prize amounts/rubrics from other Vultr events. Ask Vultr staff about model entitlement/schema/image request format only after recording a concrete failed request without secrets.
