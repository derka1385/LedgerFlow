# Live demo and submission specification

Target: a clear four-minute product demonstration backed by actual recorded evidence. This document describes what to build and record; no demo run/video/public URL exists from this preparation.

## Primary story

“The company keeps its workbook. The agent adapts to its layout, executes a real change in an isolated Vultr runtime, and proves what it changed before anyone approves it.”

Use a newly authored balanced, redacted workbook and a clear paper receipt. Keep the user's actual SSE workbook private unless its display is explicitly authorized. Its pre-existing imbalance is a useful technical finding, but it should not obscure the primary flow. A separate compatibility/audit screen can show the factual discrepancy with private fields hidden.

The unfamiliar workbook must actually be uploaded and mapped in the demonstration. Do not preselect its mapping invisibly or switch to a hidden bundled workbook. A rehearsed input is acceptable; pretending a fixed coordinate lookup is adaptive onboarding is not.

## Four-minute script

| Time | Visible action | Evidence / spoken point |
|---|---|---|
| 0:00–0:20 | Open public HTTPS app on desktop; show account context | Vultr backend is the central state/orchestration system |
| 0:20–0:50 | Upload unfamiliar supported workbook; inspect recognized sheets/accounts/write regions; owner confirms | Mapping evidence points to actual cells; no template migration |
| 0:50–1:15 | Phone photographs receipt and uploads to same workspace | Real phone → server event visible on desktop; image fields/evidence shown |
| 1:15–1:45 | Agent extracts, plans and generates Python; show execution timeline/code drawer | Actual VSI model/request metadata; code runs on Vultr, not in browser/API process |
| 1:45–2:20 | Show independent report, balanced new entry and cell diff | Exact amounts/accounts; no unauthorized edits; original hash preserved |
| 2:20–2:45 | Accountant approves; download and open exact workbook | Approved hash matches committed/downloaded bytes; native opening if verified |
| 2:45–3:20 | Run protected dummy-file probe then short timeout probe | Actual blocked read and container termination, limits and destruction shown |
| 3:20–3:45 | Complete safe job after probes; show original/current history | Application survived; capacity recovered; no financial mutation from probes |
| 3:45–4:00 | Show second layout result, architecture and evidence index | Same account semantics, different cell mapping; concise limits and public links |

Provider latency can exceed these slots. Record a longer honest version if necessary and edit with clear time compression; never replace failed live output with fabricated logs. Check organizer video length/format requirements onsite.

## Hypothetical accounting example

SEK 125.00 total, explicit SEK 25.00 tax, confirmed office supplies and company bank payment. Semantic entry: debit 6110 100.00, debit 2640 25.00, credit 1940 125.00. In the T-account adapter split the bank credit into two contra-referenced rows, preserving the workbook's single-reference convention. In the journal adapter use three rows.

This assumes the configured demo tax treatment is confirmed. The receipt image alone does not authorize a tax deduction or establish the paying bank account. The UI should show these as confirmed context rather than quietly guessing.

## Containment presentation

Use fixed admin-only diagnostic probes described in [SECURITY](SECURITY.md). The protected dummy really exists on the host, outside mounts; a staged readable control proves the probe ran. Show exception/denial from the actual workload, host-side bind/runtime configuration, unchanged dummy/source hashes and destruction status. Do not show a fake environment file filled with real credentials.

For the loop probe, show the five-second diagnostic deadline, supervisor termination reason, elapsed time, app liveness and no orphan. Then run a real safe job. A model saying “I cannot access that file” or a stopped UI spinner is not containment proof.

Do not automatically retry hostile code into a more permissive runtime. Recovery means resources were cleaned and a newly authorized safe job succeeds. If showing self-repair, use a separate harmless ordinary programming error and the bounded repair path, with the actual stderr/corrected program/result visible. Clearly identify a deliberately injected diagnostic fault if used.

## Second-layout proof

Use a journal with different sheet/header placement from the T-account workbook. Upload/map it independently; show its actual generated candidate and per-row diff. The same declared receipt entry should map to journal rows rather than T-account reference/amount pairs. If only one adapter passed by freeze, remove two-layout claims and state the limitation.

## Evidence checklist

For the recorded release retain:

* source Git commit/tag and actual dependency/runtime/image versions;
* Vultr host instance ID/region and deployed origin (redact private administration data);
* sanitized VSI model/request metadata and request outcomes;
* original/base, plan, mapping, code, candidate and report hashes;
* actual stdout/stderr, timing, resource and cleanup records;
* independent diff and accounting verification, including known limitations;
* human approval tuple/actor/time and exact committed version;
* controlled dummy/timeout/liveness/recovery evidence;
* a successful native Excel opening record if that behavior is claimed;
* final repo/demo/video URLs and submission confirmation.

## Submission README additions

At the event add a short problem statement, supported workbook profiles, deployment/setup prerequisites, exact run/test commands that actually work, environment variable names without values, demo URL, playable video link, architecture, containment policy, evidence links and candid limitations. The current preparation README is not a substitute for application setup documentation.

Use a public GitHub repository after the event's eligibility/publication rules are confirmed. Check ignored files and the actual staged Git diff for images, student identity, receipts, keys, session tokens and raw logs before publishing. Do not commit the user's Downloads workbook. Generated dummy probe content is harmless, but still distinguish it from a real secret.

## Rehearsal and truthful fallbacks

Rehearse once with fresh workbook/run IDs and no cached mapping. Test both phone Wi-Fi and a practical alternative network before recording. Keep a local copy of the genuine completed recording and permitted artifacts. If VSI or the network fails during live judging, show the recorded execution and identify its timestamp/commit; do not present it as a current live request.

If native Excel is unavailable, download the actual artifact and say native opening was not verified. If the SSE-specific writer fails feature preservation, show its read-only audit and the actually supported simpler workbook, with scope stated plainly. If secure execution or approval correctness fails, do not present the result as a functioning financial agent.

Do not claim tax compliance, universal compatibility, zero risk, guaranteed accuracy, EU-only processing or production-ready hostile-tenant security. State the demonstrated behavior precisely: executed changes in two bounded layout families, verified deltas, explicit review and measured containment under the deployed configuration.
