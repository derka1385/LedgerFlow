# Final red-team review

These are the ten most likely technical failures, ordered by delivery risk and consequence. Probabilities were not measured. Each has an observable gate, not just a reassuring statement.

| Rank | Failure and concrete trigger | Consequence | Mitigation / release gate |
|---|---|---|---|
| 1 | Model image/schema path fails for the selected account or returns confidently wrong amounts | Main demo cannot start, or bad financial proposal | Actual VSI entitlement/image/schema probes before 11:30; null unknowns, strict field evidence and correction; at most two model candidates |
| 2 | SSE file saved through an unsupported-library round trip or naïve XML serialization | Validation extensions/protection/opaque parts lost; Excel repair warning | Targeted existing-cell writer; unchanged part hashes and x14 byte checks; native Excel open; otherwise explicitly limit write support |
| 3 | Existing zero check mistaken for complete accounting balance | Pre-existing 87,976 discrepancy hidden; false correctness claim | Independent complete mapped baseline, formula-posting evaluation, default review hold, explicit acknowledgement only for delta supervision |
| 4 | Supervisor exposes arbitrary Docker mounts/argv or backend has daemon access | Generated workload can reach host secrets/originals | Fixed protocol and root-owned policy, no API Docker access, runsc/non-root/no-network, actual host-inspected C1/C2/S14 tests |
| 5 | Candidate changes after validation or approval regenerates bytes | Human approves one workbook, another gets committed | Stop/freeze before verification, immutable content addressing, approval hash tuple, no generation after approval, wrong-hash negative test |
| 6 | Two approvals or repeated mobile/HTTP requests race | Duplicate postings or lost workbook update | Tenant-scoped idempotency, committed source-key uniqueness, short atomic CAS commit, concurrent approval/response-loss tests |
| 7 | Worker dies but sandbox/retry survives, or output is lost when tmpfs disappears | Orphan compute, stalled app, missing candidate | Independent supervisor lifetime, reaper/fencing, host-owned quota work mount, stopped-job bounded export, crash/recovery tests |
| 8 | Model chooses wrong payment/tax/account context despite balanced numbers | Plausible but wrong bookkeeping | Confirm policy/payment separately from image; match actual chart; human entry review; unsupported payroll/FX/refund held |
| 9 | DNS/HTTPS/phone HEIC/SSE proxy issue appears late | Public desktop demo works but real mobile flow fails | Deployed real-phone JPEG/PNG path before lunch, file-picker fallback, early certificate/proxy test, reconnect snapshot |
| 10 | Team implements the full specification breadth before a vertical slice | No working artifact/video by submission | Hard hourly gates, one receipt category, scoped writer, defer P1; freeze features at 17:00; record by 17:00 and submit by 18:30 |

## Cross-cutting challenges to the design

**The writer is the hardest custom component.** Byte-preserving XML mutation is not a free shortcut. Existing blank cell forms, secure parsing and unchanged-byte validation narrow it, but native Excel compatibility must still be tested. Do not spend the entire day on universal preservation.

**The model cannot establish accounting truth.** Independent software can prove money conservation and exact approved cells, not that a photographed expense is legally deductible or actually belongs to the company. Those are confirmed policy/evidence and human decisions.

**Shared-host isolation has residual risk.** gVisor reduces attack exposure; host bugs, supervisor bugs and malicious file-parser vulnerabilities remain possible. Separate parser/verifier jobs and invited synthetic-data demo access keep scope honest.

**Mapping reuse can be dangerously overbroad.** Full-file fingerprints change after every transaction, while too-small layout fingerprints miss instruction/formula changes. Keep a documented canonical structural fingerprint and recheck occupancy every time.

**A baseline acknowledgement is narrowly scoped.** It can acknowledge this exact pre-existing discrepancy and permit balanced new deltas. It cannot waive a changed formula, unknown active part, unsafe runtime, unsupported evaluation or wrong output.

**Cost savings do not justify operational fragility.** Model-catalog rates are tiny relative to developer time, while account billing metadata conflicts and vision reliability is unmeasured. Pick the first model that passes the actual workload gate and record its real usage.

**SQLite version matters.** Verify the linked runtime and patched WAL behavior, or use rollback journal mode. A familiar SQL API does not establish the OS library's patch level.

## Final go/no-go review at 17:00

Go only for claimed functionality that has an actual deployed receipt run, independently verified candidate, correct exact-artifact approval, observed cleanup, real containment evidence and reachable product URL. Remove unsupported feature claims from the UI/README/video. Preserve failures in internal test results; do not rewrite a `not_run` test as a pass.

The target is a convincing, scoped secure execution product. This handoff is the technical foundation; the event team still has to implement and demonstrate it.
