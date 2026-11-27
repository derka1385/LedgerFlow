# LedgerFlow live demonstration script

The primary path is the **browser app** on the demo laptop, with real Vultr inference and the real Docker sandbox. The phone
and the native macOS shell are optional extras. Times come from runs on 27 November (`benchmark/results/e2e_live.json`,
`demo/out/final_suite_*.json`); anything not timed is marked.

## 0. Before the session (not on stage)

1. Docker Desktop running: `docker info` answers. On the demo Mac it sometimes needs a second full quit and reopen.
2. Rehearsal, about 60 s, proves inference, sandbox and verifier right now:
   ```bash
   python3 demo/final_suite.py --spawn
   ```
   Go on only if it ends with `0 failed`.
3. Start the demo:
   ```bash
   sh demo/start_demo.sh
   ```
   The first line must contain `inference: Vultr qwen3.8-27b (reasoning_effort=minimal, codegen prompt v2…)`.
4. In window A (finance), open `http://localhost:8790` and sign in with `owner-demo`. Go to **Excel Workbooks**, choose
   `demo/workbook/Nordvik_Trading_AB_T-accounts.xlsx` as the Workbook file, click **Upload and inspect**, then **Confirm
   mapping** and wait for "Mapping confirmed."
5. In window B (employee), a second browser profile or a private window, sign in with `employee-demo`. Optional: the phone
   on the same Wi-Fi at the URL `start_demo.sh` printed (plain HTTP, not verified on a device).
6. Open `demo/workbook/Nordvik_Trading_AB_T-accounts.xlsx` in Excel and leave it open: this is the "before" file.
7. Have the printed `1_success_receipt` and `3_adversarial_receipt` at hand, or keep the PNGs ready to upload.

## 1. The 90-second version

| Time | Say | Do | Expect on screen |
|---|---|---|---|
| 0:00 | "This is a company's real Excel ledger. LedgerFlow will add a receipt to it without breaking anything." | Show the workbook in Excel for 3 seconds | T-accounts, 20 accounts |
| 0:08 | "An employee snaps a receipt." | Window B: **Scan**, then **Upload a file** (or **Take photo**), pick `1_success_receipt.png`, then **Use this photo** | "Receipt submitted." |
| 0:15 | "A Vultr-hosted model reads it. Our rules, not the model, decide debit and credit. The model then writes a Python program, which runs in a locked sandbox, and an independent verifier checks the actual file." | Window A: **Transactions**, open the new run | Status moves from reading to generating code, sandbox and verifying. **About 16–23 s measured from upload to ready.** Talk over it. |
| 0:40 | "Here is the evidence: the receipt beside the entry, and exactly which cells will change." | Point at 6110 D 1 250,00, 2640 D 312,50, 1940 C 1 562,50 and the cell list | Verifier passed; button **Approve and write 8 cells** |
| 0:55 | "I approve this exact file. Its hash is what I sign." | Click **Approve and write 8 cells** | **Committed** (not timed separately; about 1 s on the laptop) |
| 1:00 | "The new version, in Excel." | **Download .xlsx**, open it next to the original | New rows in 6110, 2640 and 1940; everything else unchanged |
| 1:15 | "And when someone tries to trick it…" | Say the containment result (13/13, section 2 step 5) and the injection receipt being held | — |
| 1:30 | End | | |

## 2. The full 3-minute version

1. **Context (0:00–0:15).** Show the workbook in Excel. "Small Swedish companies keep their books in Excel. We don't replace the workbook; we write into it safely."
2. **Happy path (0:15–1:15).** As in the 90-second version:
   - Window B: **Scan** → **Upload a file** → `1_success_receipt.png` → **Use this photo**.
   - Window A: **Transactions**, open the run. While it processes (16–23 s), open **Agent Activity** to show the live events: extraction by `qwen3.8-27b`, code generated, sandbox created, started, exited, destroyed, validation completed.
   - Return to the run. Show the evidence and the cell diff, then click **Approve and write 8 cells** and wait for **Committed**.
3. **Excel comparison (1:15–1:40).** Click **Download .xlsx** and open it beside the original:
   - Office supplies (6110) has a new debit row: `R7 [6110]` / `S7 1250`.
   - Input VAT (2640) has a new debit row: `R8 [2640]` / `S8 312.50`.
   - Bank (1940) has two credit rows: `K24 [1940]` / `L24 312.50` and `A57 [1940]` / `B57 1250`. Each debit is posted against the bank on its own row (T-account convention).
   - Formulas, drop-downs and formatting are untouched. The original file is unchanged: it is version 1 in **Audit History** or Versions.
4. **Duplicate (1:40–2:00).** Window B: upload `2_duplicate_receipt.png`, or photograph the printed receipt 1 again. After **about 9–10 s** the run shows **Possible duplicate.** Nothing is written. Say: "Same supplier, total and receipt number as the run we just booked."
5. **Security moment (2:00–2:45).**
   - Upload `3_adversarial_receipt.png`. After **about 9 s** it is held for security review: the printed text asked the AI to book to equity 2081 and to run a command. Say: "It is treated as data. Nothing was written. The model can only propose accounts from the allowed list, and receipt text never reaches the code-generation prompt."
   - Then **Security** → **Run containment test**. **About 11 s.** The probe lines show `Network is unreachable` and `Read-only file system`, no secrets, an infinite loop killed at the deadline, and the container destroyed. Say: "This is our own hostile program in the same sandbox the generated code uses."
6. **Close (2:45–3:00).** "Live Vultr inference, generated code, a sandbox, an independent verifier, and a human approval bound to a file hash. On our synthetic benchmark the chosen model reached the expected outcome on 22 of 22 receipts, at about 0.4 US cents each. In the final integrated run, 4 receipts were committed and 3 were correctly held for review." Use exactly these wordings, no wider claim.

## 3. Fallbacks (each one is a fallback, say so out loud)

| Failure | Fallback | What to say |
|---|---|---|
| The native macOS or iPhone app misbehaves | **Browser app** at `http://localhost:8790`. It is the primary path anyway. | Nothing, or "same app in the browser". |
| Phone cannot reach the laptop (Wi-Fi, no HTTPS) | Upload the PNG from window B with **Upload a file**. | "Uploading the photo from the laptop." |
| Vultr inference slow or down (the run shows "Inference failed (…)") | **FALLBACK, recorded evidence**: open `demo/out/final_suite_*.json` and `benchmark/results/e2e_live.json`; both carry `model_id: qwen3.8-27b` and `mock: false`, with timestamps. Never present a mocked run as live. | "Vultr isn't answering right now. This is the recorded live run from today at [time]." |
| Docker not answering (runs fail with `SANDBOX_UNAVAILABLE`) | Quit and reopen Docker Desktop (allow 1–2 minutes, sometimes twice), then `python3 demo/containment_demo.py`. If it is still down: **FALLBACK, recorded evidence** in `BENCHMARK_RESULTS.md`, sandbox containment section. | "The sandbox host is down; LedgerFlow refuses to run code without it. Here is the recorded containment run." |
| Excel will not open the file | Show the cell diff in the run's review screen, plus the downloaded file in Quick Look or Numbers. | "Same eight cells." |
| Anything stuck in the backend | `sh demo/reset_demo.sh`, `sh demo/start_demo.sh`, then re-upload the workbook (about 30 s). | — |
