"""Final end-to-end run of the integrated application with REAL Vultr inference, REAL sandbox, REAL Excel edits.

  python3 benchmark/e2e_live.py [--excel]

Starts the DEV MOCK API (the backend the frontend talks to) with --dotenv, so the key comes from the git-ignored .env
and the model from config/inference.json. Drives the same HTTP contract as the UI: onboarding, receipt upload,
run, approval bound to the exact file hash, commit. Then re-reads the committed workbook independently and, with
--excel, opens a scratch copy in Microsoft Excel and reads the written cells back. Writes benchmark/results/e2e_live.json.
The key is never printed; the output is checked for it before writing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
API = REPO / "frontend" / "dev-mock-api"
sys.path[:0] = [str(REPO / "accounting"), str(API), str(HERE)]
from ledgerflow_accounting import Workbook, baseline, detect_mapping  # noqa: E402
import test_mock_api as T  # noqa: E402
import vsi  # noqa: E402

FIX = REPO / "fixtures" / "synthetic"
CORPUS = {c["id"]: c for c in json.loads((HERE / "corpus" / "corpus.json").read_text())}
FIXCASES = {c["case_id"]: c for c in json.loads((FIX / "cases.json").read_text())}
TERMINAL = {"AWAITING_APPROVAL", "NEEDS_REVIEW", "DUPLICATE_REVIEW", "FAILED", "REJECTED", "COMMITTED"}

# (id, image path, what a correct system does, expected entry if it commits)
SCENARIOS = [
    ("S1", FIX / "receipts" / "E1.png", "commit", FIXCASES["E1"]["expected_entry"], "Card receipt, office supplies (demo receipt)"),
    ("S2", FIX / "receipts" / "E2.png", "commit", FIXCASES["E2"]["expected_entry"], "Unpaid supplier invoice -> accounts payable"),
    ("S3", HERE / "corpus" / "R03.png", "commit", CORPUS["R03"]["expected"]["entry"], "Train ticket, 6 % VAT"),
    ("S4", HERE / "corpus" / "R01.png", "commit", CORPUS["R01"]["expected"]["entry"], "Card receipt, two items"),
    ("S5", HERE / "corpus" / "R16.png", "hold:DUPLICATE_REVIEW", None, "Second photo of S4's receipt"),
    ("S6", FIX / "receipts" / "B27.png", "hold:SECURITY_REVIEW", None, "Receipt carrying instructions to the AI"),
    ("S7", HERE / "corpus" / "R05.png", "hold:PAYMENT_CONTEXT_REQUIRED", None, "Paid by Swish: paying account not evidenced"),
]


def start_server() -> tuple[subprocess.Popen, str, str]:
    port = T.free_port()
    env = {k: v for k, v in os.environ.items() if not k.startswith(("VULTR_", "LEDGERFLOW_VSI_"))}  # config + .env only
    env["PORT"] = str(port)
    env["PYTHONUNBUFFERED"] = "1"  # the start line must arrive now, not when the buffer fills
    proc = subprocess.Popen([sys.executable, str(API / "server.py"), "--dotenv"], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    banner = proc.stdout.readline().strip()

    def drain():  # keep the pipe empty, or the server blocks once its request log fills the buffer
        with open("/tmp/lf_e2e_server.log", "w") as log:
            for line in proc.stdout:
                log.write(line)
    __import__("threading").Thread(target=drain, daemon=True).start()
    base = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            urllib.request.urlopen(base + "/api/v1/health/live", timeout=1)
            break
        except OSError:
            time.sleep(0.2)
    return proc, base, banner


def triples(entry):
    return [[ln["account_id"], ln["side"], ln["amount_minor"]] for ln in (entry or {}).get("lines", [])]


def excel_readback(xlsx: bytes, cells: list[str]) -> dict:
    """Open a scratch copy in Microsoft Excel (read only, closed without saving) and read the written cells."""
    d = Path(tempfile.mkdtemp(prefix="lf_excel_"))
    f = d / "ledgerflow_e2e_check.xlsx"
    f.write_bytes(xlsx)
    reads = "\n".join(f'set end of out to (value of range "{c}" of worksheet "T-Accounts" of wb as text)' for c in cells)
    script = f'''
tell application "Microsoft Excel"
    set wb to open workbook workbook file name (POSIX file "{f}" as text) read only true
    set out to {{}}
    {reads}
    set n to count of worksheets of wb
    close wb saving no
end tell
return (n as text) & "|" & (out as text)
'''
    try:
        try:
            p = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=90)
        except subprocess.TimeoutExpired:
            return {"opened": False, "worksheets": None, "values": None,
                    "error": "Excel did not answer within 90 s (a file-access or other dialog is probably waiting on screen)"}
        ok = p.returncode == 0
        n, _, vals = p.stdout.strip().partition("|")
        return {"opened": ok, "worksheets": int(n) if ok and n.isdigit() else None, "values": vals if ok else None,
                "error": None if ok else p.stderr.strip()[-300:]}
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main() -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("--excel", action="store_true", help="also open the committed workbook in Microsoft Excel and read the cells back")
    args = ap.parse_args()
    if not vsi.load_dotenv() or not os.environ.get("VULTR_INFERENCE_API_KEY"):
        raise SystemExit("needs VULTR_INFERENCE_API_KEY in the repo .env")
    key = os.environ["VULTR_INFERENCE_API_KEY"]
    t_start = time.monotonic()
    proc, base, banner = start_server()
    rows = []
    try:
        owner, up = T.onboard(base)
        acct = T.Client(base)
        session = acct.login("accountant-demo")
        emp = T.Client(base)
        emp.login("employee-demo")
        original = (FIX / "nordvik_t_accounts.xlsx").read_bytes()
        for sid, img, want, want_entry, title in SCENARIOS:
            st, targets, _ = emp.req("GET", "/upload-targets")
            t = targets["items"][0]
            st, doc, _ = emp.req("POST", f"/workbooks/{t['workbook_id']}/documents", files={"file": (img.name, img.read_bytes())},
                                 fields={"client_upload_id": f"e2e_{sid}"})
            t0 = time.monotonic()
            st, run, _ = emp.req("POST", "/runs", {"workbook_id": t["workbook_id"], "document_id": doc["document_id"],
                                                   "expected_base_version_id": t["base_version_id"], "expected_base_sha256": t["base_sha256"],
                                                   "mapping_id": t["mapping_id"], "mapping_version": t["mapping_version"], "client_request_id": sid})
            if st != 202:
                rows.append({"id": sid, "title": title, "expected": want, "observed": f"run refused HTTP {st}: {run}", "as_expected": False})
                continue
            snap = T.wait_state(acct, run["run_id"], TERMINAL, timeout=240)
            ready_s = round(time.monotonic() - t0, 1)
            commit = None
            if snap["state"] == "AWAITING_APPROVAL" and want == "commit":
                st, res, _ = acct.req("POST", f"/runs/{run['run_id']}/approval", T.approval_body(acct, run["run_id"]))
                commit = res.get("commit") if st == 200 else None
                snap = T.wait_state(acct, run["run_id"], {"COMMITTED", "FAILED", "STALE_BASE"}, timeout=60) if st == 200 else snap
            ev = T.read_sse(base, acct, run["run_id"])
            ext = next((e for e in ev if e["event_type"] == "extraction.completed"), {})
            gens = [e for e in ev if e["event_type"] == "code.generated"]
            observed = snap["state"] if snap["state"] not in ("NEEDS_REVIEW", "DUPLICATE_REVIEW") else f"hold:{snap['state_reason']}"
            if snap["state"] == "COMMITTED":
                observed = "commit"
            ok = observed == want and (want != "commit" or triples(snap.get("entry")) == want_entry)
            usage = (ext.get("data") or {}).get("usage") or []
            rows.append({"id": sid, "title": title, "image": str(img.relative_to(REPO)), "expected": want, "observed": observed,
                         "state_reason": snap["state_reason"], "as_expected": ok,
                         "entry": triples(snap.get("entry")), "expected_entry": want_entry,
                         "reading": {"mock": (ext.get("data") or {}).get("mock"), "model_id": (ext.get("data") or {}).get("model_id"),
                                     "mode": (ext.get("data") or {}).get("mode"),
                                     "tokens_in": sum((u or {}).get("prompt_tokens") or 0 for u in usage),
                                     "tokens_out": sum((u or {}).get("completion_tokens") or 0 for u in usage)},
                         "code": [{"model_id": g["data"].get("model_id"), "mock": g["data"].get("mock")} for g in gens],
                         "attempts": snap.get("attempt_count"), "validation": snap.get("validation_summary"),
                         "commit_sha256": (commit or {}).get("artifact_sha256"), "seconds_to_ready": ready_s})
            print(f"  {sid} {title}: {observed} ({'as expected' if ok else 'UNEXPECTED, wanted ' + want}) in {ready_s} s", flush=True)
        st, vers, _ = acct.req("GET", f"/workbooks/{up['workbook_id']}/versions")
        cur = vers["items"][0]
        st, final, _ = acct.req("GET", f"/artifacts/{cur['artifact_id']}/download", raw=True)
        wb, wb0 = Workbook(final), Workbook(original)
        b, b0 = baseline(wb, detect_mapping(wb)), baseline(wb0, detect_mapping(wb0))
        committed_gross = sum(next(x[2] for x in r["entry"] if x[1] == "credit") for r in rows if r["observed"] == "commit")
        written = sorted(set(wb.cells("T-Accounts")) - set(wb0.cells("T-Accounts")))
        final_check = {"versions": len(vers["items"]), "final_sha256": hashlib.sha256(final).hexdigest(),
                       "debit_increase_minor": b["debits_minor"] - b0["debits_minor"], "credit_increase_minor": b["credits_minor"] - b0["credits_minor"],
                       "expected_increase_minor": committed_gross, "difference_minor_before_after": [b0["difference_minor"], b["difference_minor"]],
                       "validation_ranges_before_after": [len(wb0.validation_sqrefs()), len(wb.validation_sqrefs())],
                       "cells_written": len(written)}
        final_check["balanced_and_complete"] = (final_check["debit_increase_minor"] == final_check["credit_increase_minor"] == committed_gross
                                                and b["difference_minor"] == b0["difference_minor"]
                                                and final_check["validation_ranges_before_after"][0] == final_check["validation_ranges_before_after"][1])
        if args.excel:
            final_check["excel"] = excel_readback(final, written[:6]) | {"cells_read": written[:6]}
    finally:
        proc.terminate()
    n_ok = sum(r["as_expected"] for r in rows)
    reads = [r["reading"] for r in rows if r.get("reading")]
    out = {"schema_version": "ledgerflow.e2e_live.v1", "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "server_banner": banner, "session_inference": session.get("inference"), "duration_s": round(time.monotonic() - t_start, 1),
           "scenarios": rows, "final_workbook": final_check,
           "summary": {"receipts": len(rows), "as_expected": n_ok, "committed": sum(r["observed"] == "commit" for r in rows),
                       "all_reading_live": all(x["mock"] is False for x in reads) and bool(reads),
                       "models_seen": sorted({x["model_id"] for x in reads if x["model_id"]} | {c["model_id"] for r in rows for c in r.get("code", [])}),
                       "workbook_balanced_and_complete": final_check["balanced_and_complete"],
                       "excel_opened": (final_check.get("excel") or {}).get("opened"),
                       "limitation": "One sequential session on a development Mac with Docker Desktop, DEV MOCK API backend (not Codex's), "
                                     "7 synthetic receipts; held receipts were not released by a human in this run."}}
    text = json.dumps(out, indent=1, ensure_ascii=False) + "\n"
    if key in text:
        raise SystemExit("refusing to write: the key appeared in the results")
    (HERE / "results" / "e2e_live.json").write_text(text, encoding="utf-8")
    print(f"wrote benchmark/results/e2e_live.json: {n_ok}/{len(rows)} as expected, workbook balanced: {final_check['balanced_and_complete']}")
    return out


if __name__ == "__main__":
    main()
