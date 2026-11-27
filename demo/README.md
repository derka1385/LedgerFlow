# LedgerFlow demo package

Everything here is fictional: Nordvik Trading AB, its suppliers, org numbers and amounts. Real parts: Vultr Serverless
Inference (`qwen3.8-27b`, reasoning effort minimal, codegen prompt v2), the Docker sandbox, the independent verifier and
the Excel file. Nothing is mocked: `start_demo.sh` refuses to start without the key and Docker.

| File | What it is |
|---|---|
| `workbook/Nordvik_Trading_AB_T-accounts.xlsx` | Clean T-account workbook: 20 accounts, opening balances, 5 earlier postings, data validations, a cash-control formula. SHA-256 in `expected_outcomes.json`. |
| `receipts/1_success_receipt.pdf/.png` | Papperskompaniet Söder AB, 1 562,50 SEK, card ****4821. Must be posted, verified, approved and committed. |
| `receipts/2_duplicate_receipt.pdf/.png` | A second photo of receipt 1. Must be held as a duplicate. In the room, photographing the printed receipt 1 a second time does the same. |
| `receipts/3_adversarial_receipt.pdf/.png` | Kontorsvaruhuset AB, 437,50 SEK, with printed instructions to the AI. Must be held for security review; nothing written. |
| `expected_outcomes.json` | Expected entries, expected cells (from LedgerFlow's allocator on the clean workbook), expected holds and verifier result. |
| `start_demo.sh` / `reset_demo.sh` | Start the live demo on port 8790 / stop it and clean only what it created. |
| `final_suite.py` | The 10-step release workflow plus duplicate, security and containment checks, with JSON evidence in `demo/out/`. |
| `containment_demo.py` | Stand-alone sandbox containment demonstration (real Docker). |
| `build_demo.py` | Regenerates the workbook copy, receipts and expected outcomes. |

## Expected outcomes

| Step | Receipt | Expected | Entry (SEK) |
|---|---|---|---|
| 1 | Success | Awaiting approval, verifier pass (8 cells), then committed as version 2 | 6110 Office supplies D 1 250,00 · 2640 Input VAT D 312,50 · 1940 Bank C 1 562,50 |
| 2 | Duplicate | `DUPLICATE_REVIEW`, nothing written | none |
| 3 | Adversarial | `NEEDS_REVIEW` / `SECURITY_REVIEW`, flag `SEC-INJECTION-TEXT`, nothing written | none (6110 / 2640 / 1940 for 437,50 if a human releases it) |

Expected cells for step 1 on the clean workbook: `R7 [6110]`, `S7 1250`, `R8 [2640]`, `S8 312.50`, `K24 [1940]`, `L24 312.50`,
`A57 [1940]`, `B57 1250` (T-account convention: each debit is posted against the bank account on its own row).

## Prerequisites (once)

1. Docker Desktop running (`docker info` answers; on the development Mac it sometimes needs a second full quit/reopen) and `docker pull python:3.12-slim`.
2. The Vultr inference key in the git-ignored repo `.env`: `VULTR_INFERENCE_API_KEY=...` (file mode 600). Never paste it in a chat or a terminal history.
3. `npm --prefix frontend ci && npm --prefix frontend run build` (the backend serves `frontend/dist`).
4. Print `receipts/1_success_receipt.pdf` and `receipts/3_adversarial_receipt.pdf` at 100 % (80 mm wide), if you want to photograph them.

## Run it

```bash
sh demo/start_demo.sh
```

Open the printed URL, sign in with `owner-demo` (finance) and, in a second window or on the phone, `employee-demo`. The
step-by-step script with timings is in [`../DEMO_SCRIPT.md`](../DEMO_SCRIPT.md).

Rehearse or prove the whole flow without the UI (about 60 s, a few cents of inference):

```bash
python3 demo/final_suite.py --spawn --excel
```

`--excel` opens a scratch copy in Microsoft Excel: macOS may ask once to grant Excel access to the file; someone must click
"Grant Access", otherwise that step reports a timeout. Against a deployed backend:
`python3 demo/final_suite.py --base https://HOST --owner-invite … --accountant-invite … --employee-invite …`.

Sandbox containment on its own (about 11 s):

```bash
python3 demo/containment_demo.py
```

## Reset between rehearsals

```bash
sh demo/reset_demo.sh
```

It stops only the backend recorded in `demo/.run/server.pid` (after checking its command line), removes only leftover
containers named `lf_run_*` (the LedgerFlow sandbox prefix) and deletes `demo/.run/`. It never touches `.env`, the demo
assets, `demo/out/` evidence, Docker itself, other containers, other ports or other projects. The backend keeps its data in
memory, so a restart is a clean state: re-upload the workbook as the first step.
