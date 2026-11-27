# LedgerFlow: technical evidence for the jury

27 November 2026. Every number below comes from a file in this repository; the file is named next to it. Evidence comes from
four kinds of test, labelled throughout:

- **Deterministic**: LedgerFlow's own rules and verifier, no model involved.
- **Scripted recovery**: the real orchestration code driven by a local script that plays the model. It measures the retry mechanism, not a model.
- **Local Docker**: a real hardened container on the development Mac (Docker Desktop, macOS).
- **Live Vultr**: real calls to Vultr Serverless Inference.

Nothing here was measured on a Vultr VM or a public deployment: neither exists yet (see Limitations).

## 1. What LedgerFlow does, and what is different

An employee photographs a receipt. A Vultr-hosted model reads it. LedgerFlow's deterministic rules decide the double entry
(the model never chooses debits and credits). The model then writes a Python program that edits the company's **existing**
Excel workbook. That program runs in a locked-down sandbox. An independent verifier, which contains no AI, re-reads the
resulting file and compares it with the plan. A human approves that exact file, by hash, and LedgerFlow commits it as a new
version.

What is different:

- **The model writes the edit, not the bookkeeping.** Accounts come from the company's own chart, constrained by policy. Amounts and sides come from rules, and the plan is fixed before any code exists.
- **Proof before approval.** The approver sees the evidence for each cell that will change and the verifier's checks. The approval is bound to the SHA-256 of the exact candidate file, so a different file cannot be committed with it.
- **The workbook stays intact.** Writes are surgical XML patches. Formulas, formatting and data validations stay byte-identical; a normal openpyxl save would drop them (section 6).
- **Unsafe cases stop.** Missing payment evidence, VAT that does not add up, duplicates and instructions printed on a receipt are held for a human. LedgerFlow does not guess in those cases.

## 2. Architecture

```
iPhone / browser / macOS shell ──HTTPS*──► LedgerFlow API (DEV MOCK API today; Codex's backend has health routes only)
                                              │
      1 read receipt  ──────────────────────► Vultr Serverless Inference  qwen3.8-27b, reasoning_effort=minimal
      2 propose account (from the chart) ───►   (OpenAI-compatible, json_schema output, key only on the server)
      3 rules: TransactionV1 -> EntryV1 (deterministic, accounting/ledgerflow_accounting/admit.py)
      4 plan: exact cells (deterministic allocator)
      5 generate Python for the plan ───────► Vultr Serverless Inference (codegen prompt v2)
      6 static screen ─► Docker sandbox: no network, read-only root, non-root, no capabilities, 1 CPU, 512 MB,
                         128 pids, 128 MiB tmpfs /work, deadline kill, container destroyed
      7 independent verifier reads the produced .xlsx (12 mandatory checks + T-account checks, no AI)
      8 human approval bound to {base, candidate, plan, mapping, report} hashes ─► commit new version (v1 kept)
```
\*HTTPS for the public deployment, which does not exist yet. The local demo runs on `http://localhost`.

Configuration is one file, `config/inference.json`. It holds the model, the reasoning effort, timeouts and the SHA-256 of
the three system prompts; `frontend/dev-mock-api/test_inference_config.py` fails if any of them drifts.

## 3. Hackathon fit

The event's judging rubric was not confirmed in our planning notes (`docs/HACKATHON_EXECUTION.md`). This table shows how
the build matches the event's theme as we understood it.

| Theme | Status | Evidence |
|---|---|---|
| Uses Vultr Serverless Inference | **Live, verified** | `benchmark/results/live_run{1,2}_*.json`, `e2e_live.json`, `demo/out/final_suite_*.json` |
| An agent that generates and executes code | **Live, verified**: the model writes a fresh Python program for each plan, which runs and is verified | 11/11 generated programs passed on the first try (live run 2), steps 4–6 of the final suite |
| Sandboxed execution | **Local Docker, verified**; **on Vultr infrastructure: not established** | 13/13 containment probes; `DEPLOYMENT.md` gate not passed |
| Real-world value | Excel-based bookkeeping for small Swedish companies; Swedish VAT and receipt rules | Section 8 |
| Working demo | Browser app + live backend, end to end | `demo/`, `DEMO_SCRIPT.md`, `demo/out/ui_live_browser_test.json` |

## 4. Measured results, with sample sizes

### Live Vultr

| Measurement | Result | Sample | Source |
|---|---|---|---|
| Expected outcome reached, synthetic benchmark (booked right, or correctly held) | **22/22** (run 2), 21/22 (run 1) | 22 synthetic, typeset receipts, temperature 0 | `live_run2_codegen_prompt_v2.json`, `live_run1_codegen_prompt_v1.json` |
| Critical facts invented | 0 | 12 critical fields x 22 receipts | same |
| Receipts with injected instructions flagged | 3/3 | 3 injection receipts | same |
| Generated programs verified on the first try | 11/11 | 11 plans, real sandbox | same |
| Median receipt-reading time | 6.3 s | 22 calls, from the Mac to `api.vultrinference.com` | same |
| Final integrated run | **7/7 as expected: 4 committed, 3 correctly held** (duplicate, injection, Swish without paying account) | 7 receipts, one session, 121.9 s | `benchmark/results/e2e_live.json` |
| Release suite on the demo assets | 16/17 steps passed, 0 failed, 1 not run (opening in Excel needed a click on screen) | 17 steps, 59.1 s | `demo/out/final_suite_2026-11-27T131821Z.json` |
| Browser UI, live backend, real commit | 12/12 checks | 1 headless Chrome session | `demo/out/ui_live_browser_test.json` |

The 22/22 is a correct-outcome rate on our synthetic benchmark. It is **not** a measure of general accounting accuracy.

### Deterministic, scripted and local Docker

| Measurement | Result | Kind | Source |
|---|---|---|---|
| Correct entry or correct stop reason, perfect reading | 21/21 | Deterministic | `benchmark/results/benchmark_results.json` |
| Detectable reading errors stopped before writing | 63/63 (of 95 perturbations; 3 classes are undetectable by rules by design, see Limitations) | Deterministic | same |
| Duplicate scenarios held | 6/6, 0 false positives in 4 genuine repeats | Deterministic | same |
| Workbook layouts handled (post or refuse correctly) | 10/10 | Deterministic | same |
| Faulty first programs recovered by one retry | 8/8 | **Scripted recovery** | same |
| Tampered workbooks rejected by the verifier with a named check | 16/16 | Local Docker | same |
| Sandbox escape probes contained | 13/13 | Local Docker | same |

## 5. Model selection and measured cost

We compared 18 configurations: 9 vision models from the live Vultr catalog, each with the model's default reasoning and with
minimal reasoning. All received the same 22 receipts and 11 code plans. The 8 viable minimal-reasoning configurations were
then measured again with the corrected codegen prompt. We picked from the measurements only. The rule, in order: correct
outcomes, then no invented critical facts, then injections caught, then cost, then latency.

| Configuration (run 2) | Expected outcome | Invented critical | Code 1st try | Read p50 | USD / receipt |
|---|---|---|---|---|---|
| **qwen3.8-27b, minimal** (chosen) | 22/22 | 0 | 11/11 | 6.3 s | 0.0042 |
| mimo-v2.6-flash, minimal (budget fallback) | 21/22 | 1 | 10/11 | 5.5 s | 0.00085 |
| qwen3.8-flash-next, minimal | 21/22 | 1 | 11/11 | 4.1 s | 0.00095 |

- A difference of one receipt in 22 is a tie at this sample size.
- With the model's default reasoning, reasoning tokens exhausted the 4,000-token budget or hit the 45 s timeout; up to 15/22 calls failed.
- Cost = tokens reported by Vultr × catalog list price. Computed spend for the comparison: 1.57 USD (run 1) + 0.38 USD (run 2). The billed amount is in the Vultr console.
- A final live run read 7 receipts at about 600 input and 1,400 output tokens per read.

## 6. Excel integrity

- **Only the planned cells change.** On the demo workbook, the committed file differs from the original in exactly the 8 planned cells. Debits and credits both rose by 1,562.50 SEK, the trial-balance gap stayed unchanged, and all data-validation ranges were preserved (`final_suite` step 6b, re-checked outside the backend).
- **Validations survive.** On an anonymized copy of a real course workbook, a write keeps **66/66** data-validation ranges; an openpyxl load and save keeps **0/66** (deterministic).
- **The rest of the package is untouched.** 26 of 27 package parts stay byte-identical: only the edited sheet changes.
- **The original is preserved.** It stays as version 1. The demo file on disk and version 1 in the backend have the same SHA-256 before and after the run (final suite step 10).
- **Excel opens the result.** Microsoft Excel opened the committed workbook read-only and read the written cells back (`e2e_live.json`, 12:40 UTC). In the 13:18 suite this step was not run, because macOS was waiting for a file-access click.

## 7. Sandbox, verification, approval

- **Containment.** In local Docker, these were all contained: network, DNS, writes to the root filesystem, writes to the input, writes to `/tmp`, a canary secret placed in the host environment, root, capabilities, the Docker socket, a fork bomb, a 1.5 GB memory bomb, an infinite loop, and filling `/work` (it stops at 128 MiB). 15 hostile programs were run on purpose, including 4 that evade the static screen; all were contained. A control run without the sandbox flags did reach a host listener, which shows the egress probes can detect a breach.
- **Static screen.** Before execution, a static screen refuses 11/11 known-dangerous patterns. It is a tripwire, not the security boundary.
- **Verifier.** It reads the produced file itself. It checks that the write set is exact, that cells outside the plan are unchanged, that formulas are unchanged, that features are preserved, that no active content (macros, external links) was added, that the new entry balances, and that the T-account placement is correct. Each of the 16 tamper classes was refused with a named check.
- **Human approval.** Approval is bound to the hashes. A tampered candidate hash returns HTTP 409, and only the exact verified file is committed.

## 8. Swedish receipt rules (Kvittion specification) against the implementation

| Spec rule | What LedgerFlow does today | Evidence | Not supported → where it goes |
|---|---|---|---|
| Read seller, org. no., date, serial no., amount, VAT per rate, payment method | Reads seller, org. no., date, receipt number, total, net, VAT, one VAT rate, payment method and status, card's last four digits | 98.1 % critical fields (live, qwen3.8-27b run 2) | Address, time, item lines, control code: not read. **Two VAT rates on one receipt → `TAX_REVIEW_REQUIRED`** (R21) |
| Warn above SEK 4,000 (full invoice: buyer name and address) | No receipt or invoice number above 4,000 → `TAX_REVIEW_REQUIRED`. With a number: posted, and **the approver sees a warning to check buyer name, address and seller VAT number** (added today, non-blocking; entries unchanged) | R20; `test_above_4000_sek_warns_about_full_invoice_fields` | Buyer details are not extracted: a human checks them |
| Check the VAT; warn when it cannot be calculated | VAT missing → review; VAT ≠ rate × net → review; net + VAT ≠ total → `AMOUNTS_INCONSISTENT`; rates 25/12/6 % accepted, 0 % = tax-free path | R08, R09, M02–M04 | Reverse charge, foreign VAT, margin schemes: not supported (non-SEK → `CURRENCY_UNSUPPORTED`) |
| Seller identity needed for the deduction | Missing org. no. → `TAX_REVIEW_REQUIRED` | M10 | — |
| Entertainment: purpose and attendees | Meals with guests → no account proposed (`NONE_SUITABLE`) → `ACCOUNT_REVIEW_REQUIRED` | R22 | Purpose, attendees and deduction limits: not captured; a human decides |
| Who paid | Company card (last four digits match) → bank 1940; cash → 1910; another card, Swish or transfer → `PAYMENT_CONTEXT_REQUIRED`; payment never assumed | R04–R06, S7 | Employee reimbursement (no liability account in the chart), project and cost centre: not supported |
| Duplicate check (amount, date, seller or image hash) | Same file; or same supplier (org. no. or normalised name) + total + receipt number; with no number, same supplier + date + total; checked against committed and in-flight runs | 6/6, 0/4 false positives; demo step 11; e2e S5 | Near-duplicates with a different total are not caught |
| Unpaid supplier invoice | Credited to payables 2440 | R02, E2 | Payment matching (bank lines): not supported |
| Period and date | Closed period or future date → review | R18, R19 | — |
| Image quality | Blurred, rotated and faded photos read correctly in the benchmark; "poor legibility" → review | R10–R12 | Real phone photos are not in the corpus |
| 7-year WORM archive, "safe to throw away", BankID, roles, bank/PSD2 matching, Kivra, PDF/HEIC/e-mail capture, SIE/Fortnox export, EU-only processing | **Not implemented** | — | Out of scope for the hackathon build. `qwen3.8-27b` is served from a US datacenter per the Vultr catalog, so EU-only AI processing is **not** met |

## 9. Known limitations

- **No public deployment or production backend.** The Vultr VM stack is validated only in mocked plans (`DEPLOYMENT.md`). There is no public HTTPS application yet. Codex's backend has health routes only, so every end-to-end result above ran on the DEV MOCK API with real inference and a local Docker sandbox.
- **Measurement scope.** All runs happened on one development Mac. Sandbox results come from Docker Desktop, not from the planned gVisor runtime on the Vultr VM.
- **Corpus.** 22 synthetic, typeset receipts from fictional companies, plus 7 in the final run and 3 in the demo; no real phone photos. Results can vary by one receipt from run to run.
- **Errors rules cannot catch.** A wrong day within the open period, a decimal comma lost on every amount, and a wrong but allowed expense account all get through the rules. The evidence-linked review and the human approval are the control for these.
- **Not a statutory ledger.** A T-account workbook is not statutory bookkeeping. Voucher data lives in LedgerFlow's audit log.
- **No guarantees.** We make no security or regulatory guarantee; this is a hackathon build.
- **EU processing.** Inference runs in a US datacenter.
- **iPhone.** Capture from a real iPhone has not been verified by this QA pass; the iOS project was not compiled here (`APPLE_PLATFORM_HANDOFF.md`).
