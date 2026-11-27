"""Contract conformance check: does a backend serve what the LedgerFlow UI needs?

Runs the UI's real flow over HTTP against ANY backend (Codex's, or the dev mock) and
checks every response for the fields the frontend reads (frontend/src/lib/types.ts).
Uses no mock-only route. Prints one line per step; exit code 0 only if all pass.

  python3 frontend/contract/check_backend.py --base https://<host> \
      --owner-invite <tok> --accountant-invite <tok> --employee-invite <tok> \
      --workbook fixtures/synthetic/nordvik_t_accounts.xlsx --receipt fixtures/synthetic/receipts/E1.png

The receipt must reach AWAITING_APPROVAL on that backend (a fixture on the mock, any clear receipt with real inference).
Pass --no-approve to stop before committing.
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import socket
import sys
import time
import urllib.error
import urllib.request
import uuid
from urllib.parse import urlparse

# Fields the UI reads, per response (dotted paths; "[]" = every list item). Source: frontend/src/lib/types.ts + pages.
REQUIRED = {
    "session": ["user_id", "role", "tenant_id", "csrf_token", "expires_at"],
    "workbook_upload": ["workbook_id", "version_id", "sha256", "status"],
    "workbook": ["workbook_id", "display_name", "status", "current_version_id", "current_sha256", "version_count"],
    "mapping": ["mapping_id", "mapping_version", "mapping_sha256", "status"],
    "upload_targets": ["items[].workbook_id", "items[].display_name", "items[].base_version_id", "items[].base_sha256",
                       "items[].mapping_id", "items[].mapping_version"],
    "document": ["document_id", "sha256", "status"],
    "run_created": ["run_id", "state", "events_url"],
    "run": ["run_id", "revision", "workbook_id", "document_id", "state", "state_reason", "base_version_id", "mapping_version",
            "attempt_count", "last_event_sequence", "transaction", "entry", "plan_sha256", "validation_summary",
            "candidate_sha256", "commit", "created_at", "updated_at"],
    "run_list": ["items[].run_id", "items[].state", "items[].updated_at"],
    "diff": ["base_version_id", "base_sha256", "candidate_sha256", "plan_sha256", "mapping_sha256", "policy_version",
             "validation.result", "validation.report_sha256", "validation.verifier_version", "validation.checks[].check_id",
             "validation.checks[].status", "validation.checks[].detail", "validation.cell_diff[].cell", "validation.cell_diff[].after",
             "validation.cell_diff[].account_id", "validation.cell_diff[].side", "validation.cell_diff[].reason",
             "validation.account_deltas[].account_id", "validation.limitations"],
    "commit": ["commit.commit_id", "commit.version_id", "commit.artifact_sha256", "commit.committed_at"],
    "event": ["schema_version", "event_id", "sequence", "event_type", "occurred_at", "message", "data"],
    "versions": ["items[].version_id", "items[].sha256", "items[].created_at"],
}
MANDATORY_CHECKS = ["archive_safe", "exact_write_set", "source_preconditions", "account_allocation", "new_entry_balanced",
                    "non_target_cells_unchanged", "formulas_unchanged", "formula_postings_stable", "features_preserved",
                    "no_new_active_content", "artifact_hash_match", "cleanup_confirmed"]
EXTENSIONS_UI_USES = ["run.review_items", "commit.artifact_id", "commit.audit_artifact_id", "run.code_artifact_id"]


def missing(obj, paths: list[str]) -> list[str]:
    out = []
    for p in paths:
        def walk(o, parts, trail):
            if not parts:
                return
            head, rest = parts[0], parts[1:]
            if head.endswith("[]"):
                key = head[:-2]
                if not isinstance(o, dict) or key not in o or not isinstance(o[key], list):
                    out.append(trail + head)
                    return
                for item in o[key]:
                    walk(item, rest, trail + head + ".")
            elif not isinstance(o, dict) or head not in o:
                out.append(trail + head)
            else:
                walk(o[head], rest, trail + head + ".")
        walk(obj, p.split("."), "")
    return sorted(set(out))


class Client:
    def __init__(self, base):
        self.base, self.csrf = base.rstrip("/"), None
        self.jar = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def call(self, method, path, body=None, files=None, fields=None, raw=False):
        headers = {"Origin": self.base}
        data = None
        if files:
            b = uuid.uuid4().hex
            parts = [f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in (fields or {}).items()]
            for k, (fn, content) in files.items():
                parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{fn}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()
                             + content + b"\r\n")
            data, headers["Content-Type"] = b"".join(parts) + f"--{b}--\r\n".encode(), f"multipart/form-data; boundary={b}"
        elif body is not None:
            data, headers["Content-Type"] = json.dumps(body).encode(), "application/json"
        if method != "GET":
            headers["Idempotency-Key"] = "chk_" + uuid.uuid4().hex
            if self.csrf:
                headers["X-CSRF-Token"] = self.csrf
        try:
            with self.op.open(urllib.request.Request(self.base + "/api/v1" + path, data=data, method=method, headers=headers), timeout=60) as r:
                c = r.read()
                return r.status, (c if raw else json.loads(c or b"{}"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def login(self, invite):
        st, s = self.call("POST", "/auth/session", {"invite_token": invite})
        self.csrf = s.get("csrf_token")
        return st, s


class Report:
    def __init__(self):
        self.fails = 0

    def step(self, name, ok, detail=""):
        self.fails += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  -> {detail}" if detail else ""))
        return ok

    def shape(self, name, st, obj, key, want=(200, 201, 202)):
        miss = missing(obj, REQUIRED[key]) if st in want else []
        return self.step(name, st in want and not miss, f"HTTP {st}" + (f", missing {miss}" if miss else "") +
                         (f", error {obj.get('error')}" if st not in want else ""))


def read_events(c: Client, run_id: str, seconds=2.0) -> list[dict]:
    import http.client
    u = urlparse(c.base)
    conn = (http.client.HTTPSConnection if u.scheme == "https" else http.client.HTTPConnection)(u.hostname, u.port, timeout=seconds)
    cookie = "; ".join(f"{ck.name}={ck.value}" for ck in c.jar)
    conn.request("GET", f"/api/v1/runs/{run_id}/events", headers={"Cookie": cookie, "Last-Event-ID": "0", "Accept": "text/event-stream"})
    resp = conn.getresponse()
    buf = b""
    try:
        while True:
            line = resp.fp.readline()
            if not line:
                break
            buf += line
    except (TimeoutError, socket.timeout):
        pass
    conn.close()
    return [json.loads(ln[6:]) for ln in buf.decode().splitlines() if ln.startswith("data: ")], resp.getheader("Content-Type")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--owner-invite", required=True)
    ap.add_argument("--accountant-invite", required=True)
    ap.add_argument("--employee-invite", required=True)
    ap.add_argument("--workbook", required=True)
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--no-approve", action="store_true")
    a = ap.parse_args(argv)
    R = Report()
    owner, emp, acct = Client(a.base), Client(a.base), Client(a.base)
    for c, inv, nm in ((owner, a.owner_invite, "owner"), (emp, a.employee_invite, "employee"), (acct, a.accountant_invite, "accountant")):
        st, s = c.login(inv)
        R.shape(f"auth: {nm} session", st, s, "session", (201,))
    st, up = owner.call("POST", "/workbooks", files={"file": ("workbook.xlsx", open(a.workbook, "rb").read())}, fields={"display_name": "Conformance check"})
    if not R.shape("workbooks: upload", st, up, "workbook_upload"):
        return 1
    wid = up["workbook_id"]
    for _ in range(30):
        st, wb = owner.call("GET", f"/workbooks/{wid}")
        if wb.get("status") not in ("inspecting",):
            break
        time.sleep(1)
    R.shape("workbooks: get", st, wb, "workbook")
    st, insp = owner.call("GET", f"/workbooks/{wid}/inspection")
    R.step("workbooks: inspection", st == 200, f"HTTP {st}")
    st, prop = owner.call("POST", f"/workbooks/{wid}/mapping-proposals", {"base_version_id": up["version_id"], "base_sha256": up["sha256"]})
    R.step("mapping: proposal", st in (200, 202) and "mapping_id" in prop, f"HTTP {st}")
    mid = prop.get("mapping_id")
    for _ in range(30):
        st, mp = owner.call("GET", f"/workbooks/{wid}/mappings/{mid}")
        if st == 200:
            break
        time.sleep(1)
    R.shape("mapping: get", st, mp, "mapping")
    needs_ack = bool((insp.get("baseline") or {}).get("acknowledgement_required"))
    st, conf = owner.call("POST", f"/workbooks/{wid}/mappings/{mid}/confirm", {
        "expected_mapping_version": mp.get("mapping_version"), "expected_mapping_sha256": mp.get("mapping_sha256"),
        "policy_version": "policy_nordvik_v1", "confirmed_bindings": {},
        "baseline_acknowledgement": "Conformance check acknowledges pre-existing exceptions" if needs_ack else None})
    R.shape("mapping: confirm", st, conf, "mapping")
    st, tg = emp.call("GET", "/upload-targets")
    R.shape("employee: upload targets", st, tg, "upload_targets")
    t = next((x for x in tg.get("items", []) if x["workbook_id"] == wid), None)
    if not R.step("employee: workbook is an upload target", t is not None):
        return 1
    st, doc = emp.call("POST", f"/workbooks/{wid}/documents", files={"file": ("receipt.png", open(a.receipt, "rb").read())},
                       fields={"client_upload_id": "chk_" + uuid.uuid4().hex[:12]})
    R.shape("employee: document upload", st, doc, "document")
    for _ in range(30):
        st, run = emp.call("POST", "/runs", {"workbook_id": wid, "document_id": doc["document_id"], "expected_base_version_id": t["base_version_id"],
                                               "expected_base_sha256": t["base_sha256"], "mapping_id": t["mapping_id"],
                                               "mapping_version": t["mapping_version"], "client_request_id": "chk_" + uuid.uuid4().hex[:8]})
        if st != 409 or (run.get("error") or {}).get("code") != "DOCUMENT_NOT_READY":
            break
        time.sleep(1)
    if not R.shape("employee: create run", st, run, "run_created"):
        return 1
    rid = run["run_id"]
    snap = {}
    for _ in range(180):
        st, snap = acct.call("GET", f"/runs/{rid}")
        if snap.get("state") in ("AWAITING_APPROVAL", "NEEDS_REVIEW", "FAILED", "DUPLICATE_REVIEW", "REJECTED"):
            break
        time.sleep(1)
    R.shape("accountant: run snapshot", st, snap, "run")
    if not R.step("run reaches AWAITING_APPROVAL", snap.get("state") == "AWAITING_APPROVAL",
                  f"state {snap.get('state')} ({snap.get('state_reason')})"):
        return 1
    st, lst = acct.call("GET", "/runs")
    R.shape("accountant: run list", st, lst, "run_list")
    events, ctype = read_events(acct, rid)
    R.step("events: SSE content type", (ctype or "").startswith("text/event-stream"), str(ctype))
    R.step("events: replay from 0 is ordered", bool(events) and [e["sequence"] for e in events] == sorted(e["sequence"] for e in events),
           f"{len(events)} events")
    bad = [missing(e, REQUIRED["event"]) for e in events if missing(e, REQUIRED["event"])]
    R.step("events: ExecutionEventV1 fields", not bad, str(bad[:2]))
    kinds = {e["event_type"] for e in events}
    for k in ("code.generated", "sandbox.created", "sandbox.exited", "sandbox.destroyed", "validation.completed"):
        R.step(f"events: {k} present", k in kinds)
    st, diff = acct.call("GET", f"/runs/{rid}/diff")
    R.shape("accountant: diff", st, diff, "diff")
    got = {c["check_id"]: c["status"] for c in (diff.get("validation") or {}).get("checks", [])}
    R.step("diff: 12 mandatory checks present", all(m in got for m in MANDATORY_CHECKS), str([m for m in MANDATORY_CHECKS if m not in got]))
    R.step("diff: validation result pass", (diff.get("validation") or {}).get("result") == "pass")
    for ext in EXTENSIONS_UI_USES:
        obj, key = ext.split(".")
        src = snap if obj == "run" else None
        if src is not None:
            print(f"INFO  extension {ext}: {'present' if key in src else 'absent (UI degrades gracefully)'}")
    body = {"decision": "approve", "base_version_id": diff.get("base_version_id"), "base_sha256": diff.get("base_sha256"),
            "candidate_sha256": diff.get("candidate_sha256"), "plan_sha256": diff.get("plan_sha256"), "mapping_sha256": diff.get("mapping_sha256"),
            "validation_report_sha256": (diff.get("validation") or {}).get("report_sha256"), "policy_version": diff.get("policy_version")}
    st, err = emp.call("POST", f"/runs/{rid}/approval", body)
    R.step("security: employee cannot approve (403)", st == 403, f"HTTP {st}")
    st, err = acct.call("POST", f"/runs/{rid}/approval", {**body, "candidate_sha256": "0" * 64})
    R.step("security: tampered hash tuple refused (409)", st == 409, f"HTTP {st} {(err.get('error') or {}).get('code')}")
    if not a.no_approve:
        st, res = acct.call("POST", f"/runs/{rid}/approval", body)
        R.shape("accountant: approve and commit", st, res, "commit", (200,))
        st, vers = acct.call("GET", f"/workbooks/{wid}/versions")
        R.shape("versions: list", st, vers, "versions")
        R.step("versions: committed hash is the approved candidate", any(v.get("sha256") == body["candidate_sha256"] for v in vers.get("items", [])))
    print(f"\n{'ALL PASS' if R.fails == 0 else f'{R.fails} FAILED'}")
    return 0 if R.fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
