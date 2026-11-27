"""Final release suite: the 10-step demo workflow plus duplicate, security and containment checks, with evidence.

Local (starts the backend the frontend uses, real Vultr inference from .env, real Docker sandbox):
  python3 demo/final_suite.py --spawn --excel
Against a deployed backend (e.g. the public Vultr URL once it exists):
  python3 demo/final_suite.py --base https://HOST --owner-invite ... --accountant-invite ... --employee-invite ...

Writes demo/out/final_suite_<UTC>.json. Exit code 0 only if every step passed. Nothing is mocked here: if the backend
reports mock inference or a non-Docker runtime, the corresponding step FAILS. The API key is never printed.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path[:0] = [str(REPO / "accounting"), str(REPO / "frontend" / "dev-mock-api"), str(REPO / "benchmark")]
from ledgerflow_accounting import Workbook, baseline, detect_mapping  # noqa: E402
import test_mock_api as T  # noqa: E402

EXP = json.loads((HERE / "expected_outcomes.json").read_text())
WB = REPO / EXP["workbook"]["file"]
R = {r["step"]: r for r in EXP["receipts"]}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class Suite:
    def __init__(self):
        self.steps, self.t0 = [], time.monotonic()

    def check(self, sid: str, title: str, ok, evidence) -> bool:
        """ok=None records a step that was not run (never counted as passed)."""
        self.steps.append({"step": sid, "title": title, "pass": None if ok is None else bool(ok), "evidence": evidence})
        print(f"  [{'SKIP' if ok is None else 'PASS' if ok else 'FAIL'}] {sid} {title}: {json.dumps(evidence, ensure_ascii=False, default=str)[:180]}", flush=True)
        return ok


def submit(c: T.Client, img: Path, tag: str) -> tuple[int, dict]:
    st, targets, _ = c.req("GET", "/upload-targets")
    t = targets["items"][0]
    st, doc, _ = c.req("POST", f"/workbooks/{t['workbook_id']}/documents", files={"file": (img.name, img.read_bytes())},
                       fields={"client_upload_id": f"final_{tag}_{int(time.time())}"})
    if st != 202:
        return st, doc
    return c.req("POST", "/runs", {"workbook_id": t["workbook_id"], "document_id": doc["document_id"],
                                   "expected_base_version_id": t["base_version_id"], "expected_base_sha256": t["base_sha256"],
                                   "mapping_id": t["mapping_id"], "mapping_version": t["mapping_version"], "client_request_id": tag})[:2]


def run_suite(base: str, invites: dict, excel: bool) -> dict:
    s = Suite()
    original_file_sha_before = sha(WB.read_bytes())
    s.check("0", "Demo workbook on disk matches the published hash", original_file_sha_before == EXP["workbook"]["sha256"],
            {"sha256": original_file_sha_before[:16]})
    owner, acct, emp = T.Client(base), T.Client(base), T.Client(base)
    sess = owner.login(invites["owner"])
    acct.login(invites["accountant"])
    emp.login(invites["employee"])
    s.check("0b", "Backend session reports real inference", sess.get("inference") in ("vultr", None),
            {"backend": sess.get("backend"), "inference": sess.get("inference")})

    # onboarding with the demo workbook
    st, up, _ = owner.req("POST", "/workbooks", files={"file": (WB.name, WB.read_bytes())}, fields={"display_name": "Nordvik Trading AB"})
    wid = up["workbook_id"]
    st, prop, _ = owner.req("POST", f"/workbooks/{wid}/mapping-proposals", {"base_version_id": up["version_id"], "base_sha256": up["sha256"]})
    st, mp, _ = owner.req("GET", f"/workbooks/{wid}/mappings/{prop['mapping_id']}")
    st, conf, _ = owner.req("POST", f"/workbooks/{wid}/mappings/{mp['mapping_id']}/confirm",
                            {"expected_mapping_version": 1, "expected_mapping_sha256": mp["mapping_sha256"], "policy_version": "policy_nordvik_v1",
                             "confirmed_bindings": {}, "baseline_acknowledgement": None})
    s.check("0c", "Workbook uploaded and mapping confirmed", conf.get("status") == "confirmed" and up["sha256"] == original_file_sha_before,
            {"workbook_id": wid, "uploaded_sha256": up["sha256"][:16]})

    # 1. previously unseen receipt
    t1 = time.monotonic()
    st, run = submit(emp, HERE / "receipts" / "1_success_receipt.png", "receipt1")
    s.check("1", "Upload a previously unseen receipt (employee)", st == 202, {"http": st, "run_id": run.get("run_id")})
    rid = run["run_id"]
    snap = T.wait_state(acct, rid, {"AWAITING_APPROVAL", "NEEDS_REVIEW", "DUPLICATE_REVIEW", "FAILED"}, timeout=240)
    ready_s = round(time.monotonic() - t1, 1)
    ev = T.read_sse(base, acct, rid)
    ext = next((e for e in ev if e["event_type"] == "extraction.completed"), {}).get("data", {})
    s.check("2", "Information extracted by real Vultr inference", ext.get("mock") is False and bool(ext.get("model_id")),
            {"model_id": ext.get("model_id"), "mode": ext.get("mode"), "mock": ext.get("mock")})
    entry = [[ln["account_id"], ln["side"], ln["amount_minor"]] for ln in (snap.get("entry") or {}).get("lines", [])]
    s.check("3", "Accounting entry identified", entry == R[1]["expected_entry"], {"entry": entry, "expected": R[1]["expected_entry"]})
    gens = [e["data"] for e in ev if e["event_type"] == "code.generated"]
    s.check("4", "Actual Python generated by the model", bool(gens) and all(g.get("mock") is False for g in gens),
            {"programs": len(gens), "model_id": gens[-1].get("model_id") if gens else None, "bytes": gens[-1].get("bytes") if gens else None})
    kinds = [e["event_type"] for e in ev]
    exited = next((e["data"] for e in ev if e["event_type"] == "sandbox.exited"), {})
    destroyed = next((e["data"] for e in ev if e["event_type"] == "sandbox.destroyed"), {})
    s.check("5", "Executed in the isolated sandbox, then destroyed",
            all(k in kinds for k in ("sandbox.created", "sandbox.started", "sandbox.exited", "sandbox.destroyed"))
            and exited.get("runtime") == "docker" and destroyed.get("confirmed") is True,
            {"runtime": exited.get("runtime"), "exit_code": exited.get("exit_code"), "duration_ms": exited.get("duration_ms"),
             "destroyed": destroyed.get("confirmed")})
    st, diff, _ = acct.req("GET", f"/runs/{rid}/diff")
    val = diff.get("validation", {})
    checks = {c["check_id"]: c["status"] for c in val.get("checks", [])}
    s.check("6", "Independent verifier passed on the actual file", snap["state"] == "AWAITING_APPROVAL" and val.get("result") == "pass",
            {"state": snap["state"], "result": val.get("result"), "checks_passed": sum(v == "pass" for v in checks.values()),
             "checks": len(checks), "cells_changed": len(val.get("cell_diff", [])), "seconds_to_ready": ready_s})

    # 7. approval bound to the exact artifact
    body = T.approval_body(acct, rid)
    tampered = acct.req("POST", f"/runs/{rid}/approval", {**body, "candidate_sha256": "0" * 64})[0]
    st, res, _ = acct.req("POST", f"/runs/{rid}/approval", body)
    s.check("7", "Approval bound to the exact verified artifact", tampered == 409 and st == 200,
            {"tampered_hash_http": tampered, "approval_http": st, "candidate_sha256": body["candidate_sha256"][:16]})
    st, vers, _ = acct.req("GET", f"/workbooks/{wid}/versions")
    cur = vers["items"][0]
    st, committed, _ = acct.req("GET", f"/artifacts/{cur['artifact_id']}/download", raw=True)
    s.check("8", "New workbook version committed (bytes = approved candidate)",
            len(vers["items"]) == 2 and sha(committed) == body["candidate_sha256"] == (res.get("commit") or {}).get("artifact_sha256"),
            {"versions": len(vers["items"]), "committed_sha256": sha(committed)[:16]})

    # 6b. independent re-check of the committed file, outside the backend
    orig = WB.read_bytes()
    w0, w1 = Workbook(orig), Workbook(committed)
    c0, c1 = w0.cells("T-Accounts"), w1.cells("T-Accounts")
    changed = {k: str(c1[k].value) for k in c1 if k not in c0 or str(c0[k].value) != str(c1[k].value)}
    removed = [k for k in c0 if k not in c1]
    b0, b1 = baseline(w0, detect_mapping(w0)), baseline(w1, detect_mapping(w1))
    z0, z1 = zipfile.ZipFile(io.BytesIO(orig)), zipfile.ZipFile(io.BytesIO(committed))
    same_parts = sum(1 for n in z0.namelist() if n in z1.namelist() and z0.read(n) == z1.read(n))
    want = R[1]["expected_cells_on_clean_workbook"]
    s.check("6b", "Re-checked outside the backend: only the expected cells changed, books still balance",
            set(changed) == set(want) and not removed and b1["debits_minor"] - b0["debits_minor"] == b1["credits_minor"] - b0["credits_minor"] == 156250
            and b1["difference_minor"] == b0["difference_minor"] and w0.validation_sqrefs() == w1.validation_sqrefs(),
            {"changed": changed, "debit_delta": b1["debits_minor"] - b0["debits_minor"], "credit_delta": b1["credits_minor"] - b0["credits_minor"],
             "parts_byte_identical": f"{same_parts}/{len(z0.namelist())}", "validation_ranges": len(w1.validation_sqrefs())})

    # 9. Microsoft Excel
    if excel:
        from e2e_live import excel_readback
        cells = sorted(want)
        xr = excel_readback(committed, cells)
        s.check("9", "Committed workbook opened in Microsoft Excel, cells read back", xr["opened"] and xr["worksheets"] == 3,
                {"cells": cells, "values": xr["values"], "error": xr["error"]})
    else:
        s.check("9", "Microsoft Excel open (not run: pass --excel on a Mac with Excel)", None, {"skipped": True})

    # 10. original unchanged
    st, v1, _ = acct.req("GET", f"/artifacts/{vers['items'][-1]['artifact_id']}/download", raw=True)
    s.check("10", "Original workbook unchanged (file on disk and version 1 in the backend)",
            sha(WB.read_bytes()) == original_file_sha_before == sha(v1), {"sha256": original_file_sha_before[:16], "version_1": sha(v1)[:16]})

    # duplicate and adversarial
    st, run2 = submit(emp, HERE / "receipts" / "2_duplicate_receipt.png", "duplicate")
    snap2 = T.wait_state(acct, run2["run_id"], {"AWAITING_APPROVAL", "NEEDS_REVIEW", "DUPLICATE_REVIEW", "FAILED"}, timeout=240) if st == 202 else {}
    s.check("11", "Duplicate photo held for review, nothing written", snap2.get("state") == "DUPLICATE_REVIEW",
            {"state": snap2.get("state"), "duplicate_of": snap2.get("duplicate_of"), "http": st})
    st, run3 = submit(emp, HERE / "receipts" / "3_adversarial_receipt.png", "adversarial")
    snap3 = T.wait_state(acct, run3["run_id"], {"AWAITING_APPROVAL", "NEEDS_REVIEW", "DUPLICATE_REVIEW", "FAILED"}, timeout=240) if st == 202 else {}
    st, vers2, _ = acct.req("GET", f"/workbooks/{wid}/versions")
    s.check("12", "Adversarial receipt held for security review, nothing written",
            snap3.get("state") == "NEEDS_REVIEW" and snap3.get("state_reason") == "SECURITY_REVIEW" and len(vers2["items"]) == 2,
            {"state": snap3.get("state"), "reason": snap3.get("state_reason"), "security_flags": snap3.get("security_flags"),
             "versions": len(vers2["items"])})

    # containment (same endpoint as the Security page)
    st, ct, _ = acct.req("POST", "/containment-tests", {})
    res_c = {}
    for _ in range(80):
        st, res_c, _ = acct.req("GET", f"/containment-tests/{ct['test_id']}")
        if res_c.get("state") == "DONE":
            break
        time.sleep(0.5)
    lines = "\n".join(res_c.get("lines", []))
    r = res_c.get("result") or {}
    s.check("13", "Sandbox containment probe (network, filesystem, secrets, deadline)",
            r.get("runtime") == "docker" and r.get("termination_reason") == "timeout" and r.get("destroyed") is True
            and "Network is unreachable" in lines and "Read-only file system" in lines and "CONNECTED" not in lines
            and "WRITTEN" not in lines and "run_secrets_exists: False" in lines,
            {"termination": r.get("termination_reason"), "destroyed": r.get("destroyed"), "lines": res_c.get("lines", [])[:8]})

    ok = all(x["pass"] is True for x in s.steps)
    return {"schema_version": "ledgerflow.final_suite.v1", "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "base_url": base, "duration_s": round(time.monotonic() - s.t0, 1), "all_passed": ok,
            "passed": sum(x["pass"] is True for x in s.steps), "failed": sum(x["pass"] is False for x in s.steps),
            "not_run": sum(x["pass"] is None for x in s.steps), "total": len(s.steps), "steps": s.steps}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spawn", action="store_true", help="start the local backend with --dotenv on a free port and stop it afterwards")
    ap.add_argument("--base", help="backend base URL (e.g. the public HTTPS deployment)")
    ap.add_argument("--owner-invite", default="owner-demo")
    ap.add_argument("--accountant-invite", default="accountant-demo")
    ap.add_argument("--employee-invite", default="employee-demo")
    ap.add_argument("--excel", action="store_true")
    a = ap.parse_args()
    if not (a.spawn or a.base):
        ap.error("--spawn or --base is required")
    proc = None
    base = a.base
    import vsi
    vsi.load_dotenv()  # only so the leak check below knows the key; the spawned backend reads .env itself
    if a.spawn:
        from e2e_live import start_server
        proc, base, banner = start_server()
        print(f"backend: {banner}")
        if "inference: Vultr" not in banner:
            print("REFUSING: the backend did not start with real Vultr inference (is the key in .env?)")
            proc.terminate()
            return 2
    try:
        out = run_suite(base, {"owner": a.owner_invite, "accountant": a.accountant_invite, "employee": a.employee_invite}, a.excel)
    finally:
        if proc:
            proc.terminate()
    if a.spawn:
        out["backend"] = "local DEV MOCK API started by this suite (--spawn), real Vultr inference, local Docker sandbox"
    text = json.dumps(out, indent=1, ensure_ascii=False, default=str) + "\n"
    key = os.environ.get("VULTR_INFERENCE_API_KEY")
    if key and key in text:
        print("REFUSING to write: the key appeared in the results")
        return 3
    (HERE / "out").mkdir(exist_ok=True)
    f = HERE / "out" / f"final_suite_{out['generated_at'].replace(':', '')}.json"
    f.write_text(text, encoding="utf-8")
    print(f"{out['passed']}/{out['total']} steps passed, {out['failed']} failed, {out['not_run']} not run, in {out['duration_s']} s -> {f.relative_to(REPO)}")
    return 0 if out["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
