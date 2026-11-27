"""End-to-end HTTP test of the DEV MOCK API (real rules, OOXML, verifier, Docker sandbox; mocked inference).

  python3 -m pytest frontend/dev-mock-api/test_mock_api.py -q
Needs Docker with LEDGERFLOW_SANDBOX_IMAGE available (default python:3.12-slim); skips otherwise.
"""
from __future__ import annotations

import http.cookiejar
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FIX = REPO / "fixtures" / "synthetic"
sys.path.insert(0, str(REPO / "accounting"))
sys.path.insert(0, str(HERE))
import sandbox  # noqa: E402
from ledgerflow_accounting import Workbook, baseline, detect_mapping  # noqa: E402

pytestmark = pytest.mark.skipif(not (sandbox.docker_available() and sandbox.image_available()),
                                reason=f"Docker or image {sandbox.IMAGE} unavailable")


class Client:
    def __init__(self, base: str):
        self.base, self.csrf = base, None
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def req(self, method, path, body=None, files=None, fields=None, idem=True, raw=False):
        headers = {"Origin": self.base}
        data = None
        if files is not None:
            b = uuid.uuid4().hex
            parts = []
            for k, v in (fields or {}).items():
                parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
            for k, (fname, content) in files.items():
                parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{fname}"\r\n'
                             f"Content-Type: application/octet-stream\r\n\r\n".encode() + content + b"\r\n")
            data = b"".join(parts) + f"--{b}--\r\n".encode()
            headers["Content-Type"] = f"multipart/form-data; boundary={b}"
        elif body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if method != "GET":
            if self.csrf:
                headers["X-CSRF-Token"] = self.csrf
            if idem:
                headers["Idempotency-Key"] = idem if isinstance(idem, str) else uuid.uuid4().hex
        r = urllib.request.Request(self.base + "/api/v1" + path, data=data, method=method, headers=headers)
        try:
            with self.op.open(r, timeout=60) as resp:
                content = resp.read()
                return resp.status, (content if raw else json.loads(content or b"{}")), dict(resp.headers)
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}"), dict(e.headers)

    def login(self, invite):
        st, s, _ = self.req("POST", "/auth/session", {"invite_token": invite}, idem=False)
        assert st == 201, s
        self.csrf = s["csrf_token"]
        return s


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def base_url():
    port = free_port()
    env = {**os.environ, "PORT": str(port)}
    proc = subprocess.Popen([sys.executable, str(HERE / "server.py")], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            urllib.request.urlopen(url + "/api/v1/health/live", timeout=1)
            break
        except OSError:
            time.sleep(0.2)
    yield url
    proc.terminate()


def wait_state(c: Client, rid: str, states: set, timeout=90):
    t0 = time.time()
    while time.time() - t0 < timeout:
        st, snap, _ = c.req("GET", f"/runs/{rid}")
        if snap["state"] in states:
            return snap
        time.sleep(0.5)
    raise AssertionError(f"run {rid} stuck in {snap['state']}")


def onboard(base_url) -> tuple[Client, dict]:
    owner = Client(base_url)
    owner.login("owner-demo")
    st, up, _ = owner.req("POST", "/workbooks", files={"file": ("nordvik.xlsx", (FIX / "nordvik_t_accounts.xlsx").read_bytes())},
                          fields={"display_name": "Nordvik Trading AB"})
    assert st == 202
    wid = up["workbook_id"]
    st, insp, _ = owner.req("GET", f"/workbooks/{wid}/inspection")
    assert st == 200 and insp["compatibility"]["accounts"] == 20 and insp["baseline"]["difference_minor"] == 0
    st, prop, _ = owner.req("POST", f"/workbooks/{wid}/mapping-proposals", {"base_version_id": up["version_id"], "base_sha256": up["sha256"]})
    st, mp, _ = owner.req("GET", f"/workbooks/{wid}/mappings/{prop['mapping_id']}")
    st, conf, _ = owner.req("POST", f"/workbooks/{wid}/mappings/{mp['mapping_id']}/confirm",
                            {"expected_mapping_version": 1, "expected_mapping_sha256": mp["mapping_sha256"],
                             "policy_version": "policy_nordvik_v1", "confirmed_bindings": {}, "baseline_acknowledgement": None})
    assert st == 200 and conf["status"] == "confirmed"
    return owner, up


def submit(c: Client, case: str) -> str:
    st, targets, _ = c.req("GET", "/upload-targets")
    t = targets["items"][0]
    st, doc, _ = c.req("POST", f"/workbooks/{t['workbook_id']}/documents", files={"file": (f"{case}.png", (FIX / "receipts" / f"{case}.png").read_bytes())},
                       fields={"client_upload_id": f"up_{case}_{uuid.uuid4().hex[:6]}"})
    assert st == 202, doc
    st, run, _ = c.req("POST", "/runs", {"workbook_id": t["workbook_id"], "document_id": doc["document_id"],
                                          "expected_base_version_id": t["base_version_id"], "expected_base_sha256": t["base_sha256"],
                                          "mapping_id": t["mapping_id"], "mapping_version": t["mapping_version"], "client_request_id": case})
    assert st == 202, run
    return run["run_id"]


def approval_body(c: Client, rid: str) -> dict:
    st, d, _ = c.req("GET", f"/runs/{rid}/diff")
    assert st == 200
    return {"decision": "approve", "base_version_id": d["base_version_id"], "base_sha256": d["base_sha256"],
            "candidate_sha256": d["candidate_sha256"], "plan_sha256": d["plan_sha256"], "mapping_sha256": d["mapping_sha256"],
            "validation_report_sha256": d["validation"]["report_sha256"], "policy_version": d["policy_version"]}


def test_full_flow(base_url):
    owner, up = onboard(base_url)
    emp, acct = Client(base_url), Client(base_url)
    emp.login("employee-demo")
    acct.login("accountant-demo")

    # employee cannot approve; CSRF is enforced
    rid = submit(emp, "E1")
    snap = wait_state(acct, rid, {"AWAITING_APPROVAL", "FAILED", "NEEDS_REVIEW"})
    assert snap["state"] == "AWAITING_APPROVAL", snap
    assert snap["validation_summary"]["result"] == "pass" and snap["validation_summary"]["runtime"] == "docker"
    body = approval_body(acct, rid)
    assert emp.req("POST", f"/runs/{rid}/approval", body)[0] == 403
    no_csrf = Client(base_url)
    no_csrf.op = acct.op
    assert no_csrf.req("POST", f"/runs/{rid}/approval", body)[0] == 403

    # diff is exactly the 8 planned cells and features are preserved
    st, d, _ = acct.req("GET", f"/runs/{rid}/diff")
    assert len(d["validation"]["cell_diff"]) == 8
    assert {c["check_id"]: c["status"] for c in d["validation"]["checks"]}["features_preserved"] == "pass"

    # a tampered hash tuple is refused, the exact one commits, replay is idempotent
    assert acct.req("POST", f"/runs/{rid}/approval", {**body, "candidate_sha256": "0" * 64})[0] == 409
    key = uuid.uuid4().hex
    st, res, _ = acct.req("POST", f"/runs/{rid}/approval", body, idem=key)
    assert st == 200 and res["commit"]["artifact_sha256"] == body["candidate_sha256"]
    st2, res2, h = acct.req("POST", f"/runs/{rid}/approval", body, idem=key)
    assert st2 == 200 and h.get("Idempotent-Replayed") == "true" and res2["commit"]["commit_id"] == res["commit"]["commit_id"]

    # the committed file is the candidate, and re-parses with +1,250.00 / +1,250.00
    st, xlsx, _ = acct.req("GET", f"/artifacts/{res['commit']['artifact_id']}/download", raw=True)
    wb, wb0 = Workbook(xlsx), Workbook((FIX / "nordvik_t_accounts.xlsx").read_bytes())
    b, b0 = baseline(wb, detect_mapping(wb)), baseline(wb0, detect_mapping(wb0))
    assert (b["debits_minor"] - b0["debits_minor"], b["credits_minor"] - b0["credits_minor"]) == (125000, 125000)

    # SSE replay contains the sandbox lifecycle in order
    events = read_sse(base_url, acct, rid)
    kinds = [e["event_type"] for e in events]
    for k in ("run.created", "extraction.completed", "plan.admitted", "code.generated", "sandbox.created", "sandbox.started",
              "sandbox.exited", "sandbox.destroyed", "validation.completed", "approval.created", "commit.completed"):
        assert k in kinds, k
    assert kinds.index("sandbox.destroyed") < kinds.index("validation.completed") < kinds.index("commit.completed")
    assert [e["sequence"] for e in events] == sorted(e["sequence"] for e in events)

    # exact duplicate of a committed document is refused
    st, targets, _ = emp.req("GET", "/upload-targets")
    t = targets["items"][0]
    st, doc, _ = emp.req("POST", f"/workbooks/{t['workbook_id']}/documents", files={"file": ("E1.png", (FIX / "receipts" / "E1.png").read_bytes())},
                         fields={"client_upload_id": "dup"})
    st, err, _ = emp.req("POST", "/runs", {"workbook_id": t["workbook_id"], "document_id": doc["document_id"],
                                            "expected_base_version_id": t["base_version_id"], "expected_base_sha256": t["base_sha256"],
                                            "mapping_id": t["mapping_id"], "mapping_version": t["mapping_version"]})
    assert st == 409 and err["error"]["code"] == "ALREADY_COMMITTED"


def read_sse(base_url, c: Client, rid: str, wait=2.0) -> list[dict]:
    """Read the SSE stream for `wait` seconds (it never closes by itself) and parse data lines."""
    import http.client
    from urllib.parse import urlparse

    u = urlparse(base_url)
    cookie = "; ".join(f"{ck.name}={ck.value}" for h in c.op.handlers if isinstance(h, urllib.request.HTTPCookieProcessor)
                       for ck in h.cookiejar)
    conn = http.client.HTTPConnection(u.hostname, u.port, timeout=wait)
    conn.request("GET", f"/api/v1/runs/{rid}/events", headers={"Cookie": cookie, "Last-Event-ID": "0"})
    resp = conn.getresponse()
    assert resp.status == 200 and resp.getheader("Content-Type") == "text/event-stream"
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
    return [json.loads(ln[6:]) for ln in buf.decode().splitlines() if ln.startswith("data: ")]


def test_review_correction_and_stale_base(base_url):
    owner, _ = onboard(base_url)
    acct = Client(base_url)
    acct.login("accountant-demo")
    # B11: no payment line -> NEEDS_REVIEW, accountant answers, then it validates
    rid = submit(acct, "B11")
    snap = wait_state(acct, rid, {"NEEDS_REVIEW", "AWAITING_APPROVAL", "FAILED"})
    assert snap["state"] == "NEEDS_REVIEW" and snap["state_reason"] == "PAYMENT_CONTEXT_REQUIRED"
    st, _, _ = acct.req("POST", f"/runs/{rid}/corrections", {"expected_run_revision": snap["revision"], "expected_transaction_revision": 1,
                                                              "corrections": {"payment_status": "paid", "payment_source": "company_bank"},
                                                              "reason": "Paid with company card per employee"})
    assert st == 202
    snap = wait_state(acct, rid, {"AWAITING_APPROVAL", "FAILED", "NEEDS_REVIEW"})
    assert snap["state"] == "AWAITING_APPROVAL", snap

    # E2 prepared on the same base; committing B11 first makes E2 stale; re-run lands on the new version
    rid2 = submit(acct, "E2")
    assert wait_state(acct, rid2, {"AWAITING_APPROVAL", "FAILED", "NEEDS_REVIEW"})["state"] == "AWAITING_APPROVAL"
    assert acct.req("POST", f"/runs/{rid}/approval", approval_body(acct, rid))[0] == 200
    assert wait_state(acct, rid2, {"STALE_BASE"})["state"] == "STALE_BASE"
    st, rr, _ = acct.req("POST", f"/runs/{rid2}/rerun", {})
    snap3 = wait_state(acct, rr["run_id"], {"AWAITING_APPROVAL", "FAILED", "NEEDS_REVIEW"})
    assert snap3["state"] == "AWAITING_APPROVAL"
    assert acct.req("POST", f"/runs/{rr['run_id']}/approval", approval_body(acct, rr["run_id"]))[0] == 200


def test_injection_is_held_and_containment_is_real(base_url):
    onboard(base_url)
    acct = Client(base_url)
    acct.login("accountant-demo")
    rid = submit(acct, "B27")
    snap = wait_state(acct, rid, {"NEEDS_REVIEW", "AWAITING_APPROVAL", "FAILED"})
    assert snap["state"] == "NEEDS_REVIEW" and snap["state_reason"] == "SECURITY_REVIEW"
    st, ct, _ = acct.req("POST", "/containment-tests", {})
    t0 = time.time()
    while time.time() - t0 < 40:
        st, res, _ = acct.req("GET", f"/containment-tests/{ct['test_id']}")
        if res["state"] == "DONE":
            break
        time.sleep(0.5)
    lines = "\n".join(res["lines"])
    assert res["result"]["termination_reason"] == "timeout" and res["result"]["destroyed"]
    assert "Network is unreachable" in lines and "Read-only file system" in lines and "CONNECTED" not in lines
    assert "run_secrets_exists: False" in lines


def test_correction_changes_only_the_corrected_field(base_url):
    onboard(base_url)
    acct = Client(base_url)
    acct.login("accountant-demo")
    rid = submit(acct, "B12")  # printed VAT 260,00 does not add up
    snap = wait_state(acct, rid, {"NEEDS_REVIEW", "AWAITING_APPROVAL", "FAILED"})
    assert snap["state"] == "NEEDS_REVIEW" and snap["state_reason"] in ("AMOUNTS_INCONSISTENT", "TAX_REVIEW_REQUIRED")
    t = snap["transaction"]
    unchanged = {k: t[k] for k in ("merchant_name", "gross_minor", "net_minor", "payment_status", "payment_source")}
    st, _, _ = acct.req("POST", f"/runs/{rid}/corrections", {"expected_run_revision": snap["revision"], "expected_transaction_revision": 1,
                                                              "corrections": {**unchanged, "tax_minor": 25000}, "reason": "VAT misprint"})
    assert st == 202
    snap = wait_state(acct, rid, {"AWAITING_APPROVAL", "FAILED", "NEEDS_REVIEW"})
    assert snap["state"] == "AWAITING_APPROVAL", snap.get("review_items")
    human = [e for e in snap["transaction"]["evidence"] if e["source"] == "human_confirmation"]
    assert [e["field"] for e in human] == ["tax_minor"]
