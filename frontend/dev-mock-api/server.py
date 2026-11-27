"""LedgerFlow DEV MOCK API. Not the production backend (Codex owns backend/).

Implements the subset of docs/API_CONTRACT.md the frontend needs, so the UI
can be built and tested end to end before the real backend exists.

  REAL here:   accounting rules, T-account mapping, slot allocation, OOXML
               writes, independent verifier, hardened Docker sandbox, hash-bound
               approval, versions, SSE with replay, idempotency, CSRF.
  MOCKED here: the two Vultr Serverless Inference calls. Extraction recognises
               the fixture receipts by SHA-256 (anything else asks the user to
               type the fields); code generation returns a fixed template.
               Every mocked step is labelled MOCK in events and snapshots.

Run:  python3 frontend/dev-mock-api/server.py          (port 8787)
Env:  LEDGERFLOW_SANDBOX_IMAGE (default python:3.12-slim), LEDGERFLOW_ALLOW_UNSANDBOXED=1 (dev only)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import sys
import threading
import time
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "accounting"))
sys.path.insert(0, str(HERE))

from ledgerflow_accounting import (DEFAULT_POLICY, Workbook, WorkbookError, admit, allocate, baseline,  # noqa: E402
                                   detect_mapping, verify)
import codescreen  # noqa: E402
import programs  # noqa: E402
import vsi  # noqa: E402
if "--dotenv" in sys.argv:  # opt-in: the live demo reads the key from the repo .env; tests never pass this flag
    vsi.load_dotenv()
    vsi.MODEL = os.environ.get("LEDGERFLOW_VSI_MODEL") or vsi.MODEL
import sandbox  # noqa: E402

PORT = int(os.environ.get("PORT", "8787"))
DIST = HERE.parent / "dist"
FIXTURES = REPO / "fixtures" / "synthetic"
MAX_UPLOAD = 10 * 1024 * 1024
MOCK = "MOCK (no Vultr credentials): "
COMPANY_TZ = ZoneInfo("Europe/Stockholm")
# LEDGERFLOW_STRICT_CONTRACT=1 strips every proposed extension, to prove the UI works against the written contract alone.
STRICT = os.environ.get("LEDGERFLOW_STRICT_CONTRACT") == "1"
COMPANY = {"name": "Nordvik Trading AB", "org_no": "559999-0000", "cards": ["4821"]}  # demo company settings

INVITES = {"owner-demo": ("usr_owner", "owner", "Owner (demo)"), "accountant-demo": ("usr_acct", "accountant", "Accountant (demo)"),
           "employee-demo": ("usr_emp", "employee", "Employee (demo)")}
LOCK = threading.RLock()
COND = threading.Condition(LOCK)
DB: dict = {"sessions": {}, "workbooks": {}, "versions": {}, "artifacts": {}, "mappings": {}, "documents": {}, "runs": {},
            "events": [], "idem": {}, "open_items": [], "containment": {}, "seq": 0}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def oid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, retryable: bool = False, details: dict | None = None):
        super().__init__(message)
        self.status, self.code, self.message, self.retryable, self.details = status, code, message, retryable, details or {}


# ------------------------------------------------------------------ storage helpers
def put_artifact(data: bytes, filename: str, ctype: str) -> str:
    aid = oid("art")
    DB["artifacts"][aid] = {"bytes": data, "filename": filename, "content_type": ctype, "sha256": sha(data)}
    return aid


def emit(run_id: str | None, event_type: str, state: str | None, message: str, data: dict | None = None, attempt_id=None):
    with COND:
        DB["seq"] += 1
        ev = {"schema_version": "ledgerflow.event.v1", "event_id": f"evt_{DB['seq']}", "sequence": DB["seq"], "run_id": run_id,
              "attempt_id": attempt_id, "event_type": event_type, "state": state, "occurred_at": now(),
              "message": message[:2000], "data": data or {}}
        DB["events"].append(ev)
        COND.notify_all()
        return ev


def set_state(run: dict, to: str, reason_code: str, message: str, **extra):
    frm = run["state"]
    run.update(state=to, state_reason=reason_code, updated_at=now(), revision=run["revision"] + 1, **extra)
    ev = emit(run["run_id"], "run.state_changed", to, message, {"from": frm, "to": to, "reason_code": reason_code})
    run["last_event_sequence"] = ev["sequence"]


# ------------------------------------------------------------------ fixture recognition (MOCK extraction)
def fixture_index() -> dict[str, dict]:
    cases = json.loads((FIXTURES / "cases.json").read_text())
    return {sha((FIXTURES / c["image"]).read_bytes()): c for c in cases}


FIXTURE_BY_SHA = fixture_index()

BLANK_TXN_FIELDS = ["merchant_name", "document_date", "gross_minor", "net_minor", "tax_minor", "payment_status",
                    "payment_source", "category_account_id", "tax_treatment"]


def blank_transaction(doc: dict, run: dict) -> dict:
    return {"schema_version": "ledgerflow.transaction.v1", "transaction_id": oid("txn"), "document_id": doc["document_id"],
            "tenant_id": "ten_nordvik", "revision": 1, "document_sha256": doc["sha256"], "normalized_image_sha256": doc["sha256"],
            "kind": "purchase_receipt", "merchant_name": None, "supplier_reference": None, "supplier_org_no": None,
            "document_date": None, "currency": "SEK", "gross_minor": None, "net_minor": None, "tax_minor": None, "tax_lines": [],
            "payment_status": "unknown", "payment_source": "unknown", "payment_account_id": None, "category_account_id": None,
            "tax_treatment": "unknown", "policy_version": DEFAULT_POLICY["policy_version"], "evidence": [],
            "unresolved_fields": list(BLANK_TXN_FIELDS), "confirmed_by": None, "confirmed_at": None,
            "exact_duplicate_key": doc["sha256"], "semantic_duplicate_key": None}


# ------------------------------------------------------------------ the run pipeline (worker thread)
def start_run_worker(run_id: str, from_stage: str = "EXTRACTING"):
    threading.Thread(target=_run_safely, args=(run_id, from_stage), daemon=True).start()


def _run_safely(run_id, from_stage):
    try:
        run_pipeline(run_id, from_stage)
    except Exception as exc:  # never leave a run hanging
        traceback.print_exc()
        with LOCK:
            run = DB["runs"][run_id]
            set_state(run, "FAILED", "INTERNAL_ERROR", f"Internal error in the dev mock: {type(exc).__name__}: {exc}")
            emit(run_id, "run.failed", "FAILED", str(exc))


def run_pipeline(run_id: str, from_stage: str):
    with LOCK:
        run = DB["runs"][run_id]
        doc = DB["documents"][run["document_id"]]
    time.sleep(0.4)
    if from_stage == "EXTRACTING":
        with LOCK:
            set_state(run, "EXTRACTING", "STARTED", "Reading the document.")
        time.sleep(0.8)
        if vsi.enabled():
            if not real_extraction(run, doc):
                return
            case = None
        else:
            case = FIXTURE_BY_SHA.get(doc["sha256"])
        with LOCK:
            if run.get("transaction") is not None and case is None and vsi.enabled():
                pass  # filled by real_extraction
            elif case:
                txn = json.loads(json.dumps(case["transaction"]))
                txn.update(transaction_id=oid("txn"), document_id=doc["document_id"], document_sha256=doc["sha256"],
                           normalized_image_sha256=doc["sha256"], exact_duplicate_key=doc["sha256"])
                run["transaction"] = txn
                run["security_flags"] = [case["security"]["event"]] if case.get("security") else []
                emit(run_id, "extraction.completed", "EXTRACTING",
                     MOCK + f"fixture receipt {case['case_id']} recognised by SHA-256; fields loaded from ground truth.",
                     {"mock": True, "model_id": "MOCK_INFERENCE", "fields_known": 20 - len(txn["unresolved_fields"])})
            else:
                run["transaction"] = blank_transaction(doc, run)
                run["security_flags"] = []
                emit(run_id, "extraction.completed", "EXTRACTING",
                     MOCK + "unrecognised image. Real extraction needs Vultr Serverless Inference; please type the fields.",
                     {"mock": True, "model_id": "MOCK_INFERENCE", "fields_known": 0})
            if run["security_flags"]:
                emit(run_id, "review.required", "EXTRACTING",
                     "The document contains text addressed to an AI system. It was treated as plain content; nothing it asked for was done.",
                     {"reason_code": "SEC-INJECTION-TEXT"})
                set_state(run, "NEEDS_REVIEW", "SECURITY_REVIEW", "Held for review: instruction-like text on the document.")
                return
            if dup := semantic_duplicate(run):
                set_state(run, "DUPLICATE_REVIEW", "DUPLICATE_REVIEW",
                          f"Possible duplicate of run {dup['run_id']} ({dup['state'].lower().replace('_', ' ')}): same file, or same supplier and total "
                          "with the same reference (or the same date when no reference is printed).",
                          duplicate_of=dup["run_id"])
                return
    plan_and_execute(run_id)


def real_extraction(run: dict, doc: dict) -> bool:
    """Vultr Serverless Inference calls 1 and 2. Returns False if the run was parked."""
    rid = run["run_id"]
    art = DB["artifacts"][doc["artifact_id"]]
    try:
        obj, meta = vsi.extract(art["bytes"], art["content_type"], COMPANY)
        txn, flags = vsi.to_transaction(obj, blank_transaction(doc, run), COMPANY)
        if txn.get("category_account_id") is None and txn.get("gross_minor") is not None:
            with LOCK:
                mp = DB["mappings"][run["mapping_id"]]["detected"]["accounts"]
            allowed = {c: mp[c]["name"] for c in DEFAULT_POLICY["allowed_category_accounts"] if c in mp}
            prop, meta2 = vsi.propose_account(txn, allowed)
            meta["calls"] += meta2["calls"]
            if prop["proposed_account"] != "NONE_SUITABLE":
                txn["category_account_id"] = prop["proposed_account"]
                txn["evidence"].append({"evidence_id": "vsi_category", "field": "category_account_id", "source": "receipt_image",
                                        "text": prop["rationale"][:300], "bbox": None, "page": 1, "status": "observed"})
            else:
                txn["unresolved_fields"] = sorted(set(txn["unresolved_fields"]) | {"category_account_id"})
            run["account_alternatives"] = prop.get("alternatives", [])
    except vsi.VsiError as exc:
        with LOCK:
            run["transaction"] = blank_transaction(doc, run)
            run["security_flags"] = []
            emit(rid, "review.required", "EXTRACTING", f"Inference failed ({exc.code}); type the fields to continue.", {"reason_code": exc.code})
            set_state(run, "NEEDS_REVIEW", exc.code, "Receipt could not be read automatically. Nothing was written.")
        return False
    with LOCK:
        run["transaction"] = txn
        run["security_flags"] = flags
        emit(rid, "extraction.completed", "EXTRACTING",
             f"Read by {meta['model_id']} on Vultr Serverless Inference ({meta['mode']} mode, {meta['calls']} call(s)).",
             {"mock": False, "model_id": meta["model_id"], "mode": meta["mode"], "provider_request_id": meta.get("provider_request_id"),
              "usage": meta["usage"], "fields_known": 20 - len(txn["unresolved_fields"])})
    return True


NOT_POSTED = {"REJECTED", "FAILED", "CANCELLED", "EXPIRED"}  # runs that can never post: a resubmission is not a duplicate


def _norm_name(s: str | None) -> str:
    return re.sub(r"[^0-9a-zåäöü]", "", (s or "").casefold())


def is_same_purchase(t: dict, o: dict) -> bool:
    """Same file, or same supplier + same total + (same reference, or no reference on either and the same date)."""
    if t.get("exact_duplicate_key") and t.get("exact_duplicate_key") == o.get("exact_duplicate_key"):
        return True
    if not t.get("gross_minor") or t.get("gross_minor") != o.get("gross_minor"):
        return False
    orgs = (_norm_name(t.get("supplier_org_no")), _norm_name(o.get("supplier_org_no")))
    names = (_norm_name(t.get("merchant_name")), _norm_name(o.get("merchant_name")))
    if not ((all(orgs) and orgs[0] == orgs[1]) or (names[0] and names[0] == names[1])):
        return False
    refs = (_norm_name(t.get("supplier_reference")), _norm_name(o.get("supplier_reference")))
    if all(refs):
        return refs[0] == refs[1]
    return not any(refs) and bool(t.get("document_date")) and t.get("document_date") == o.get("document_date")


def semantic_duplicate(run: dict) -> dict | None:
    """Possible duplicate among committed AND in-flight runs (two pending copies must not both be approved)."""
    t = run["transaction"]
    if run.get("duplicate_resolution") == "distinct_transaction":
        return None
    for other in DB["runs"].values():
        if other["run_id"] == run["run_id"] or other["state"] in NOT_POSTED or other["run_id"] == run.get("rerun_of") \
                or not other.get("transaction") or other.get("rerun_of") == run["run_id"]:
            continue
        if is_same_purchase(t, other["transaction"]):
            return other
    return None


def plan_and_execute(run_id: str):
    with LOCK:
        run = DB["runs"][run_id]
        set_state(run, "PLANNING", "STARTED", "Deciding the double entry from confirmed facts and company policy.")
        res = admit(run["transaction"], today=datetime.now(COMPANY_TZ).date().isoformat())  # accounting dates are company-local
        run["review_items"] = res["review"]
        run["advisories"] = res["advisories"]
        if not res["admitted"]:
            first = res["review"][0]
            emit(run_id, "review.required", "PLANNING", f"{first['message']} {first['detail']}", {"reason_code": first["code"]})
            set_state(run, "NEEDS_REVIEW", first["code"], "Needs a human answer before anything is written.")
            return
        entry = res["entry"]
        run["entry"] = entry
        ver = DB["versions"][run["base_version_id"]]
        base = DB["artifacts"][ver["artifact_id"]]["bytes"]
        wb = Workbook(base)
        mp = DB["mappings"][run["mapping_id"]]
        try:
            alloc = allocate(wb, mp["detected"], entry)
        except WorkbookError as exc:
            emit(run_id, "review.required", "PLANNING", str(exc), {"reason_code": exc.code})
            set_state(run, "NEEDS_REVIEW", exc.code, str(exc))
            return
        plan = {"schema_version": "ledgerflow.plan.v1", "plan_id": oid("plan"), "run_id": run_id,
                "transaction_id": entry["transaction_id"], "transaction_revision": entry["transaction_revision"],
                "base_version_id": ver["version_id"], "base_sha256": ver["sha256"], "mapping_id": mp["mapping_id"],
                "mapping_version": mp["mapping_version"], "mapping_sha256": mp["mapping_sha256"],
                "policy_version": entry["policy_version"], "entry": entry, **alloc, "allow_calcpr_change": False,
                "created_at": now()}
        plan["plan_sha256"] = sha(canon({k: v for k, v in plan.items() if k != "plan_sha256"}))
        run["plan"] = plan
        run["plan_sha256"] = plan["plan_sha256"]
        run["last_failure"] = None
        emit(run_id, "plan.admitted", "PLANNING", f"Plan admitted: {len(alloc['operations'])} cells in {len(alloc['posting_allocations'])} postings.",
             {"plan_sha256": plan["plan_sha256"], "operations": len(alloc["operations"])})
    for attempt in (1, 2):
        if execute_attempt(run_id, attempt, base):
            return
        with LOCK:
            if attempt == 1:
                set_state(run, "RETRY_PENDING", "VALIDATION_FAILED", "Validation failed; one repair attempt is allowed.")
                emit(run_id, "retry.scheduled", "RETRY_PENDING", "Retrying with a fresh sandbox.", {"attempt": 2})
    with LOCK:
        set_state(run, "FAILED", "VALIDATION_FAILED", "The agent could not produce a valid change. Nothing was written.")
        emit(run_id, "run.failed", "FAILED", "Budget exhausted after 2 attempts.")


def execute_attempt(run_id: str, attempt: int, base: bytes) -> bool:
    att = f"att_{run_id[4:12]}_{attempt}"
    with LOCK:
        run = DB["runs"][run_id]
        run["attempt_count"] = attempt
        set_state(run, "GENERATING_CODE", "STARTED", "Generating the Python program for this plan.")
        plan_copy, hint = run["plan"], run.get("last_failure")
    if vsi.enabled():
        try:
            text, meta = vsi.generate_program(plan_copy, hint)
        except vsi.VsiError as exc:
            with LOCK:
                run["last_failure"] = f"{exc.code}: {exc}"
                emit(run_id, "run.state_changed", run["state"], f"Code generation failed: {exc.code}", {"reason_code": exc.code}, att)
            return False
        code, label, model_id, mock = text.encode(), "Program generated by the model for this plan.", meta["model_id"], False
    else:
        code, label, model_id, mock = (programs.MOCK_GENERATED_PROGRAM.encode(),
                                       MOCK + "template program used in place of model-generated code.", "MOCK_CODEGEN_TEMPLATE", True)
    with LOCK:
        code_art = put_artifact(code, "main.py", "text/x-python; charset=utf-8")
        run["code_artifact_id"] = code_art
        emit(run_id, "code.generated", "GENERATING_CODE", label,
             {"code_artifact_id": code_art, "code_sha256": sha(code), "model_id": model_id, "mock": mock, "bytes": len(code),
              "generation_index": attempt}, att)
        findings = codescreen.screen(code.decode("utf-8", "replace"))
        if findings:  # V-SEC-02: refused before execution; not the security boundary, the sandbox is
            run["last_failure"] = "Static screen refused the program: " + "; ".join(findings[:5])
            emit(run_id, "containment.observed", run["state"], "Generated program refused before execution: " + "; ".join(findings[:3]),
                 {"reason_code": "SEC-CODE-DENIED", "findings": findings[:10]}, att)
            return False
        set_state(run, "SANDBOX_STARTING", "STARTED", "Creating a fresh isolated sandbox.")
        plan_bytes = canon(run["plan"])
    inputs = {"source.xlsx": base, "plan.json": plan_bytes, "main.py": code, **programs.helper_package()}

    def on_event(kind, data):
        with LOCK:
            if kind == "sandbox.started":
                set_state(run, "EXECUTING", "STARTED", "Running the generated Python in the sandbox.")
            emit(run_id, kind, run["state"], {"sandbox.created": "Sandbox created.", "sandbox.started": "Sandbox started."}[kind], data, att)

    result = sandbox.run(inputs, on_event=on_event)
    with LOCK:
        for stream in ("stdout", "stderr"):
            text = result[stream]
            for i in range(0, len(text), 4000):
                emit(run_id, "sandbox.log", run["state"], f"{stream} output",
                     {"stream": stream, "text": text[i:i + 4000], "truncated": False}, att)
        emit(run_id, "sandbox.exited", run["state"], f"Program exited ({result['termination_reason']}).",
             {"exit_code": result["exit_code"], "termination_reason": result["termination_reason"],
              "duration_ms": result["duration_ms"], "peak_memory_bytes": result["peak_memory_bytes"], "runtime": result["runtime"]}, att)
        if result["sandbox_id"]:
            emit(run_id, "sandbox.destroyed", run["state"],
                 "Sandbox destroyed." if result["destroyed"] else "Sandbox NOT confirmed destroyed.",
                 {"sandbox_id": result["sandbox_id"], "confirmed": result["destroyed"]}, att)
        if result["termination_reason"] == "sandbox_unavailable":
            set_state(run, "FAILED", "SANDBOX_UNAVAILABLE", result["stderr"])
            emit(run_id, "run.failed", "FAILED", result["stderr"])
            return True
        if result["output"] is None:
            run["last_failure"] = f"Program produced no candidate (exit {result['exit_code']}, {result['termination_reason']}). stderr: {result['stderr'][-1500:]}"
            return False
        set_state(run, "VERIFYING", "STARTED", "Independent verifier reading the actual output file.")
        cand = result["output"]
        rep = verify(base, cand, run["plan"], transaction=run["transaction"], cleanup_confirmed=result["destroyed"])
        rep.update(validation_id=oid("val"), run_id=run_id, attempt_id=att, plan_sha256=run["plan_sha256"],
                   mapping_sha256=run["plan"]["mapping_sha256"], policy_version=run["plan"]["policy_version"],
                   runtime=result["runtime"])
        rep["report_sha256"] = sha(canon({k: v for k, v in rep.items() if k != "report_sha256"}))
        run["validation"] = rep
        emit(run_id, "validation.completed", "VERIFYING", f"Validation {rep['result']}: "
             f"{sum(c['status'] == 'pass' for c in rep['checks'])}/{len(rep['checks'])} checks passed.",
             {"report_sha256": rep["report_sha256"], "result": rep["result"]}, att)
        if rep["result"] == "fail":
            run["last_failure"] = "; ".join(f"{c['check_id']}: {c['detail']}" for c in rep["checks"] if c["status"] == "fail")[:2000]
            return False
        run["candidate_artifact_id"] = put_artifact(cand, "candidate.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        run["candidate_sha256"] = sha(cand)
        run["validation_summary"] = {"result": rep["result"], "report_sha256": rep["report_sha256"],
                                     "checks_passed": sum(c["status"] == "pass" for c in rep["checks"]),
                                     "checks_total": len(rep["checks"]), "runtime": result["runtime"]}
        if rep["result"] == "review_required":
            pending = ", ".join(rep["not_passed_mandatory"])
            set_state(run, "NEEDS_REVIEW", "VERIFICATION_INCOMPLETE", f"Mandatory checks not passed: {pending}.")
            return True
        run["approval_expires_at"] = (datetime.now(timezone.utc) + timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ")
        set_state(run, "AWAITING_APPROVAL", "VALIDATED", "Ready for approval. Approval is bound to the exact file hash.")
        emit(run_id, "approval.created", "AWAITING_APPROVAL", "Waiting for an accountant to approve.",
             {"candidate_sha256": run["candidate_sha256"]})
        return True


# ------------------------------------------------------------------ snapshots
SNAPSHOT_KEYS = ["run_id", "revision", "workbook_id", "document_id", "state", "state_reason", "base_version_id", "mapping_version",
                 "transaction_revision", "attempt_count", "last_event_sequence", "transaction", "entry", "plan_sha256",
                 "validation_summary", "candidate_artifact_id", "candidate_sha256", "commit", "created_at", "updated_at"]
SNAPSHOT_EXTENSIONS = ["review_items", "advisories", "security_flags", "duplicate_of", "code_artifact_id", "approval_expires_at",
                       "mock_labels"]


def snapshot(run: dict, role: str) -> dict:
    s = {k: run.get(k) for k in SNAPSHOT_KEYS + ([] if STRICT else SNAPSHOT_EXTENSIONS)}
    if STRICT and s.get("commit"):
        s["commit"] = {k: v for k, v in s["commit"].items() if k not in ("artifact_id", "audit_artifact_id")}
    s["transaction_revision"] = (run.get("transaction") or {}).get("revision")
    if role == "employee":  # employees see progress, not approval data
        for k in ("candidate_artifact_id", "approval_expires_at"):
            s[k] = None
    return s


def workbook_view(wb: dict) -> dict:
    ver = DB["versions"][wb["current_version_id"]]
    mp = DB["mappings"].get(wb.get("mapping_id")) if wb.get("mapping_id") else None
    return {"workbook_id": wb["workbook_id"], "display_name": wb["display_name"], "status": wb["status"],
            "current_version_id": ver["version_id"], "current_sha256": ver["sha256"], "version_count": len(wb["versions"]),
            "mapping": None if not mp else {k: mp[k] for k in ("mapping_id", "mapping_version", "mapping_sha256", "status")},
            "compatibility": wb.get("compatibility"), "baseline_summary": wb.get("baseline_summary"), "created_at": wb["created_at"]}


# ------------------------------------------------------------------ HTTP layer
ROUTES: list[tuple[str, re.Pattern, object, tuple]] = []


def route(method: str, pattern: str, roles: tuple = ("employee", "accountant", "owner"), auth=True, idem=False):
    def deco(fn):
        ROUTES.append((method, re.compile("^/api/v1" + pattern + "$"), fn, (roles, auth, idem)))
        return fn
    return deco


class Handler(BaseHTTPRequestHandler):
    server_version = "LedgerFlowDevMock/0.1"

    def log_message(self, fmt, *args):
        sys.stderr.write("[mock-api] " + fmt % args + "\n")

    # -- plumbing
    def _json(self, status: int, obj, headers: dict | None = None):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-LedgerFlow-Backend", "DEV-MOCK")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _err(self, e: ApiError):
        self._json(e.status, {"error": {"code": e.code, "message": e.message, "retryable": e.retryable,
                                        "request_id": oid("req"), "details": e.details}})

    def _session(self):
        cookie = self.headers.get("Cookie", "")
        m = re.search(r"ledgerflow_session=([A-Za-z0-9_\-]+)", cookie)
        return DB["sessions"].get(m.group(1)) if m else None

    def _body(self) -> bytes:
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_UPLOAD + 1024 * 1024:
            raise ApiError(413, "IMAGE_TOO_LARGE", "Upload exceeds 10 MiB.")
        return self.rfile.read(n) if n else b""

    def _dispatch(self, method: str):
        url = urlparse(self.path)
        if not url.path.startswith("/api/"):
            return self._static(url.path)
        for m, rx, fn, (roles, auth, idem) in ROUTES:
            mt = rx.match(url.path)
            if m != method or not mt:
                continue
            try:
                sess = self._session()
                if auth and not sess:
                    raise ApiError(401, "SESSION_REQUIRED", "Sign in with an invite first.")
                if auth and sess["role"] not in roles:
                    raise ApiError(403, "FORBIDDEN", f"Role {sess['role']} cannot do this.")
                raw = self._body() if method in ("POST", "DELETE") else b""
                if method in ("POST", "DELETE") and auth:
                    if self.headers.get("X-CSRF-Token") != sess["csrf_token"]:
                        raise ApiError(403, "CSRF_REQUIRED", "Missing or wrong X-CSRF-Token.")
                ctx = {"session": sess, "query": parse_qs(url.query), "raw": raw, "headers": self.headers, "handler": self}
                if idem:
                    key = self.headers.get("Idempotency-Key") or ""
                    if not re.fullmatch(r"[\x21-\x7e]{16,128}", key):
                        raise ApiError(400, "IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key header (16-128 ASCII) is required.")
                    scope = (sess["user_id"], m, url.path, key)
                    with LOCK:
                        prev = DB["idem"].get(scope)
                        if prev:
                            if prev[0] != sha(raw):
                                raise ApiError(409, "IDEMPOTENCY_CONFLICT", "Same key, different request body.")
                            return self._json(prev[1], prev[2], {"Idempotent-Replayed": "true"})
                result = fn(ctx, *mt.groups())
                if result is None:  # handler streamed itself
                    return
                status, obj, *hdr = result
                if idem:
                    with LOCK:
                        DB["idem"][scope] = (sha(raw), status, obj)
                return self._json(status, obj, hdr[0] if hdr else None)
            except ApiError as e:
                return self._err(e)
            except (BrokenPipeError, ConnectionResetError):
                return
            except Exception as exc:  # noqa: BLE001
                traceback.print_exc()
                return self._err(ApiError(500, "INTERNAL", f"Dev mock error: {type(exc).__name__}"))
        return self._err(ApiError(404, "NOT_FOUND", "Unknown route."))

    def _static(self, path: str):
        if not DIST.exists():
            return self._json(404, {"error": {"code": "NO_FRONTEND_BUILD", "message": "Run `npm run build` in frontend/ or use the Vite dev server."}})
        target = (DIST / path.lstrip("/")).resolve()
        if not str(target).startswith(str(DIST.resolve())) or not target.is_file():
            target = DIST / "index.html"
        data = target.read_bytes()
        ctype = {".js": "text/javascript", ".css": "text/css", ".html": "text/html; charset=utf-8", ".svg": "image/svg+xml",
                 ".png": "image/png", ".json": "application/json"}.get(target.suffix, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_DELETE(self):
        self._dispatch("DELETE")


def parse_multipart(ctx) -> tuple[dict, dict]:
    ctype = ctx["headers"].get("Content-Type", "")
    m = re.search(r"boundary=(?:\"([^\"]+)\"|([^;]+))", ctype)
    if not m:
        raise ApiError(400, "MULTIPART_REQUIRED", "Expected multipart/form-data.")
    boundary = ("--" + (m.group(1) or m.group(2)).strip()).encode()
    fields, files = {}, {}
    for part in ctx["raw"].split(boundary)[1:-1]:
        head, _, body = part.strip(b"\r\n").partition(b"\r\n\r\n")
        h = head.decode("utf-8", "replace")
        name = re.search(r'name="([^"]*)"', h)
        fname = re.search(r'filename="([^"]*)"', h)
        if not name:
            continue
        if fname:
            files[name.group(1)] = {"filename": fname.group(1), "bytes": body.rstrip(b"\r\n") if body.endswith(b"\r\n") else body}
        else:
            fields[name.group(1)] = body.decode("utf-8", "replace").rstrip("\r\n")
    return fields, files


def jbody(ctx) -> dict:
    try:
        return json.loads(ctx["raw"] or b"{}")
    except json.JSONDecodeError as exc:
        raise ApiError(400, "MALFORMED_JSON", "Request body is not valid JSON.") from exc


def get_or_404(table: str, key: str) -> dict:
    obj = DB[table].get(key)
    if obj is None:
        raise ApiError(404, "NOT_FOUND", f"Unknown {table[:-1]}.")
    return obj


# ------------------------------------------------------------------ routes: auth
@route("POST", "/auth/session", auth=False)
def create_session(ctx):
    token = jbody(ctx).get("invite_token", "")
    if token not in INVITES:
        raise ApiError(401, "INVITE_INVALID", "Unknown invite. Dev mock invites: owner-demo, accountant-demo, employee-demo.")
    uid, role, name = INVITES[token]
    sid, csrf = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    exp = (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%dT%H:%M:%SZ")
    sess = {"user_id": uid, "role": role, "display_name": name, "tenant_id": "ten_nordvik", "csrf_token": csrf, "expires_at": exp}
    DB["sessions"][sid] = sess
    # Production: __Host-ledgerflow_session; Secure (HTTPS). Dev mock runs on http://localhost.
    extra = {} if STRICT else {"backend": "DEV-MOCK", "inference": "vultr" if vsi.enabled() else "mock"}
    return 201, {**{k: v for k, v in sess.items() if not (STRICT and k == "display_name")}, **extra}, {"Set-Cookie": f"ledgerflow_session={sid}; HttpOnly; SameSite=Lax; Path=/; Max-Age=28800"}


@route("GET", "/auth/session")
def get_session(ctx):
    if STRICT:
        return 200, {k: v for k, v in ctx["session"].items() if k != "display_name"}
    return 200, {**ctx["session"], "backend": "DEV-MOCK", "inference": "vultr" if vsi.enabled() else "mock"}


@route("DELETE", "/auth/session")
def delete_session(ctx):
    for sid, s in list(DB["sessions"].items()):
        if s is ctx["session"]:
            del DB["sessions"][sid]
    return 200, {"ok": True}, {"Set-Cookie": "ledgerflow_session=; Max-Age=0; Path=/"}


@route("GET", "/health/live", auth=False)
def health(ctx):
    return 200, {"status": "alive", "backend": "DEV-MOCK", "docker": sandbox.docker_available(), "sandbox_image": sandbox.IMAGE,
                 "inference": f"vultr:{vsi.MODEL}" if vsi.enabled() else "MOCK"}


# ------------------------------------------------------------------ routes: workbooks
@route("POST", "/workbooks", roles=("owner",), idem=True)
def upload_workbook(ctx):
    fields, files = parse_multipart(ctx)
    f = files.get("file")
    if not f or not f["bytes"]:
        raise ApiError(400, "FILE_REQUIRED", "Attach the .xlsx file.")
    if len(f["bytes"]) > MAX_UPLOAD:
        raise ApiError(413, "ARCHIVE_LIMIT", "Workbook exceeds 10 MiB.")
    data = f["bytes"]
    with LOCK:
        wid, vid = oid("wb"), oid("ver")
        art = put_artifact(data, f["filename"] or "workbook.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        DB["versions"][vid] = {"version_id": vid, "workbook_id": wid, "sha256": sha(data), "artifact_id": art, "created_at": now(),
                               "source": "upload", "commit_id": None, "run_id": None, "number": 1}
        wb = {"workbook_id": wid, "display_name": (fields.get("display_name") or f["filename"] or "Workbook")[:120],
              "status": "inspecting", "versions": [vid], "current_version_id": vid, "created_at": now(), "mapping_id": None}
        DB["workbooks"][wid] = wb
        try:
            book = Workbook(data)
            detected = detect_mapping(book)
            base = baseline(book, detected)
            wb.update(status="inspected", detected=detected, baseline=base,
                      compatibility={"supported": True, "layout": "t_accounts", "sheet": detected["sheet"],
                                     "accounts": len(detected["accounts"]), "slot_count": detected["slot_count"],
                                     "used_slots": base["used_slots"], "formulas": len(detected["formulas"]),
                                     "validation_ranges": len(book.validation_sqrefs()), "sheets": list(book.sheets)},
                      baseline_summary={k: base[k] for k in ("debits_minor", "credits_minor", "difference_minor",
                                                              "opening_debits_minor", "opening_credits_minor",
                                                              "acknowledgement_required", "evaluation_status")})
        except WorkbookError as exc:
            wb.update(status="unsupported", compatibility={"supported": False, "code": exc.code, "message": str(exc)})
    return 202, {"workbook_id": wid, "version_id": vid, "sha256": sha(data), "status": "inspecting"}


@route("GET", "/workbooks", roles=("accountant", "owner"))
def list_workbooks(ctx):
    return 200, {"items": [workbook_view(w) for w in DB["workbooks"].values()], "next_cursor": None}


@route("GET", "/workbooks/([A-Za-z0-9_\\-]+)", roles=("accountant", "owner"))
def get_workbook(ctx, wid):
    return 200, workbook_view(get_or_404("workbooks", wid))


@route("GET", "/workbooks/([A-Za-z0-9_\\-]+)/inspection", roles=("accountant", "owner"))
def get_inspection(ctx, wid):
    wb = get_or_404("workbooks", wid)
    if wb["status"] == "inspecting":
        raise ApiError(409, "INSPECTION_INCOMPLETE", "Inspection still running.")
    if wb["status"] == "unsupported":
        return 200, {"compatibility": wb["compatibility"], "baseline": None, "accounts": []}
    det, base = wb["detected"], wb["baseline"]
    accounts = [{"account_id": a["account_id"], "name": a["name"], "role": a["role"], "header_cell": a["header_cell"],
                 "debit": {k: a["debit"][k] for k in ("reference_column", "amount_column", "first_row", "last_row", "opening_balance_cell")},
                 "credit": {k: a["credit"][k] for k in ("reference_column", "amount_column", "first_row", "last_row", "opening_balance_cell")},
                 "free_debit": len(a["debit"]["writable_rows"]), "free_credit": len(a["credit"]["writable_rows"])}
                for a in det["accounts"].values()]
    return 200, {"compatibility": wb["compatibility"], "baseline": base, "accounts": accounts, "formulas": det["formulas"]}


@route("POST", "/workbooks/([A-Za-z0-9_\\-]+)/mapping-proposals", roles=("owner",), idem=True)
def propose_mapping(ctx, wid):
    wb = get_or_404("workbooks", wid)
    body = jbody(ctx)
    ver = DB["versions"][wb["current_version_id"]]
    if body.get("base_sha256") != ver["sha256"] or body.get("base_version_id") != ver["version_id"]:
        raise ApiError(409, "STALE_BASE", "The workbook changed; reload.", details={"current_version_id": ver["version_id"]})
    if wb["status"] != "inspected":
        raise ApiError(422, "UNSUPPORTED_WORKBOOK", "This workbook layout is not supported.")
    with LOCK:
        mid = oid("map")
        det = wb["detected"]
        mapping = {"schema_version": "ledgerflow.mapping.v1", "mapping_id": mid, "workbook_id": wid, "mapping_version": 1,
                   "source_sha256": ver["sha256"], "status": "proposed", "layout": "t_accounts", "currency": "SEK",
                   "money_exponent": 2, "amount_unit": "major_units", "preservation_policy": "ooxml_cell_spans_v1",
                   "policy_version": None, "detected": det, "baseline_report_sha256": sha(canon(wb["baseline"])),
                   "inspector_version": "ledgerflow-accounting 0.1.0", "adapter_version": "t_accounts-dv 0.1.0 (deterministic, no LLM)",
                   "confirmed_by": None, "confirmed_at": None, "baseline_acknowledgement": None}
        mapping["mapping_sha256"] = sha(canon({k: v for k, v in mapping.items() if k != "mapping_sha256"}))
        DB["mappings"][mid] = mapping
    return 202, {"mapping_id": mid, "status": "proposed"}


@route("GET", "/workbooks/([A-Za-z0-9_\\-]+)/mappings/([A-Za-z0-9_\\-]+)", roles=("accountant", "owner"))
def get_mapping(ctx, wid, mid):
    mp = get_or_404("mappings", mid)
    return 200, {k: v for k, v in mp.items() if k != "detected"} | {"account_count": len(mp["detected"]["accounts"]),
                                                                       "sheet": mp["detected"]["sheet"]}


@route("POST", "/workbooks/([A-Za-z0-9_\\-]+)/mappings/([A-Za-z0-9_\\-]+)/confirm", roles=("owner",), idem=True)
def confirm_mapping(ctx, wid, mid):
    wb, mp, body = get_or_404("workbooks", wid), get_or_404("mappings", mid), jbody(ctx)
    if body.get("expected_mapping_sha256") != mp["mapping_sha256"] or body.get("expected_mapping_version") != mp["mapping_version"]:
        raise ApiError(409, "MAPPING_DRIFT", "The mapping changed since you reviewed it.")
    if wb["baseline"]["acknowledgement_required"] and not body.get("baseline_acknowledgement"):
        raise ApiError(422, "BASELINE_REVIEW_REQUIRED", "Acknowledge the pre-existing exceptions first.")
    with LOCK:
        mp.update(status="confirmed", policy_version=body.get("policy_version") or DEFAULT_POLICY["policy_version"],
                  confirmed_by=ctx["session"]["user_id"], confirmed_at=now(),
                  baseline_acknowledgement=({"report_sha256": mp["baseline_report_sha256"], "base_sha256": mp["source_sha256"],
                                              "actor_id": ctx["session"]["user_id"], "acknowledged_at": now(),
                                              "reason": str(body.get("baseline_acknowledgement"))[:500]}
                                             if body.get("baseline_acknowledgement") else None))
        mp["mapping_sha256"] = sha(canon({k: v for k, v in mp.items() if k != "mapping_sha256"}))
        wb["mapping_id"] = mid
        wb["status"] = "ready"
    return 200, {k: v for k, v in mp.items() if k != "detected"}


@route("GET", "/upload-targets")
def upload_targets(ctx):
    items = []
    for wb in DB["workbooks"].values():
        if wb["status"] == "ready":
            ver, mp = DB["versions"][wb["current_version_id"]], DB["mappings"][wb["mapping_id"]]
            items.append({"workbook_id": wb["workbook_id"], "display_name": wb["display_name"], "base_version_id": ver["version_id"],
                          "base_sha256": ver["sha256"], "mapping_id": mp["mapping_id"], "mapping_version": mp["mapping_version"]})
    return 200, {"items": items}


@route("GET", "/workbooks/([A-Za-z0-9_\\-]+)/versions", roles=("accountant", "owner"))
def list_versions(ctx, wid):
    wb = get_or_404("workbooks", wid)
    items = []
    for n, vid in enumerate(wb["versions"], 1):
        v = DB["versions"][vid]
        items.append({"version_id": vid, "number": n, "sha256": v["sha256"], "artifact_id": v["artifact_id"], "created_at": v["created_at"],
                      "source": v["source"], "commit_id": v["commit_id"], "run_id": v["run_id"],
                      "is_current": vid == wb["current_version_id"]})
    return 200, {"items": list(reversed(items)), "next_cursor": None}


# ------------------------------------------------------------------ routes: documents and runs
@route("POST", "/workbooks/([A-Za-z0-9_\\-]+)/documents", idem=True)
def upload_document(ctx, wid):
    get_or_404("workbooks", wid)
    fields, files = parse_multipart(ctx)
    f = files.get("file")
    if not f or not f["bytes"]:
        raise ApiError(400, "FILE_REQUIRED", "Attach a photo.")
    data = f["bytes"]
    if len(data) > MAX_UPLOAD:
        raise ApiError(413, "IMAGE_TOO_LARGE", "Photo exceeds 10 MiB.")
    if not (data[:3] == b"\xff\xd8\xff" or data[:8] == b"\x89PNG\r\n\x1a\n"):
        raise ApiError(415, "IMAGE_UNREADABLE", "Only JPEG or PNG photos are accepted.")
    with LOCK:
        did = oid("doc")
        art = put_artifact(data, f["filename"] or "receipt", "image/png" if data[:4] == b"\x89PNG" else "image/jpeg")
        DB["documents"][did] = {"document_id": did, "workbook_id": wid, "sha256": sha(data), "artifact_id": art, "status": "ready",
                                "uploaded_by": ctx["session"]["user_id"], "client_upload_id": fields.get("client_upload_id"),
                                "created_at": now(), "fixture_case": (FIXTURE_BY_SHA.get(sha(data)) or {}).get("case_id")}
    return 202, {"document_id": did, "sha256": sha(data), "status": "normalizing"}


@route("GET", "/documents/([A-Za-z0-9_\\-]+)")
def get_document(ctx, did):
    d = get_or_404("documents", did)
    return 200, {k: d[k] for k in ("document_id", "workbook_id", "sha256", "status", "created_at")} | {
        "image_url": f"/api/v1/artifacts/{d['artifact_id']}/download"}


@route("POST", "/runs", idem=True)
def create_run(ctx):
    b = jbody(ctx)
    wb = get_or_404("workbooks", b.get("workbook_id", ""))
    doc = get_or_404("documents", b.get("document_id", ""))
    if wb["status"] != "ready" or b.get("mapping_id") != wb["mapping_id"]:
        raise ApiError(409, "MAPPING_REQUIRED", "Confirm the workbook mapping first.")
    ver = DB["versions"][wb["current_version_id"]]
    if b.get("expected_base_version_id") != ver["version_id"] or b.get("expected_base_sha256") != ver["sha256"]:
        raise ApiError(409, "STALE_BASE", "This workbook changed. Reload and try again.", details={"current_version_id": ver["version_id"]})
    for r in DB["runs"].values():
        if r["state"] == "COMMITTED" and DB["documents"][r["document_id"]]["sha256"] == doc["sha256"]:
            raise ApiError(409, "ALREADY_COMMITTED", "This exact document was already booked.",
                           details={"run_id": r["run_id"], "commit_id": r["commit"]["commit_id"]})
    with LOCK:
        rid = oid("run")
        run = {"run_id": rid, "revision": 0, "workbook_id": wb["workbook_id"], "document_id": doc["document_id"], "state": "QUEUED",
               "state_reason": "CREATED", "base_version_id": ver["version_id"], "mapping_id": wb["mapping_id"],
               "mapping_version": DB["mappings"][wb["mapping_id"]]["mapping_version"], "attempt_count": 0,
               "last_event_sequence": 0, "transaction": None, "entry": None, "plan_sha256": None, "validation_summary": None,
               "candidate_artifact_id": None, "candidate_sha256": None, "commit": None, "created_at": now(), "updated_at": now(),
               "created_by": ctx["session"]["user_id"], "client_request_id": b.get("client_request_id"),
               "mock_labels": [] if vsi.enabled() else ["extraction: MOCK_INFERENCE", "code generation: MOCK_CODEGEN_TEMPLATE"]}
        DB["runs"][rid] = run
        ev = emit(rid, "run.created", "QUEUED", "Run created.", {"document_id": doc["document_id"]})
        run["last_event_sequence"] = ev["sequence"]
    start_run_worker(rid)
    return 202, {"run_id": rid, "state": "QUEUED", "events_url": f"/api/v1/runs/{rid}/events"}


def visible_run(ctx, rid) -> dict:
    run = get_or_404("runs", rid)
    s = ctx["session"]
    if s["role"] == "employee" and run["created_by"] != s["user_id"]:
        raise ApiError(404, "NOT_FOUND", "Unknown run.")
    return run


@route("GET", "/runs")
def list_runs(ctx):
    s = ctx["session"]
    q = ctx["query"]
    items = []
    for r in sorted(DB["runs"].values(), key=lambda r: r["created_at"], reverse=True):
        if s["role"] == "employee" and r["created_by"] != s["user_id"]:
            continue
        if q.get("state") and r["state"] not in q["state"][0].split(","):
            continue
        t = r.get("transaction") or {}
        items.append({"run_id": r["run_id"], "state": r["state"], "state_reason": r["state_reason"], "workbook_id": r["workbook_id"],
                      "document_id": r["document_id"], "merchant_name": t.get("merchant_name"), "gross_minor": t.get("gross_minor"),
                      "document_date": t.get("document_date"), "kind": t.get("kind"), "validation_summary": r["validation_summary"],
                      "created_at": r["created_at"], "updated_at": r["updated_at"]})
    return 200, {"items": items[:100], "next_cursor": None}


@route("GET", "/runs/([A-Za-z0-9_\\-]+)")
def get_run(ctx, rid):
    return 200, snapshot(visible_run(ctx, rid), ctx["session"]["role"])


@route("GET", "/runs/([A-Za-z0-9_\\-]+)/events")
def run_events(ctx, rid):
    visible_run(ctx, rid)
    h = ctx["handler"]
    after = int(h.headers.get("Last-Event-ID") or (ctx["query"].get("after") or ["0"])[0] or 0)
    h.send_response(200)
    h.send_header("Content-Type", "text/event-stream")
    h.send_header("Cache-Control", "no-cache, no-transform")
    h.send_header("X-Accel-Buffering", "no")
    h.end_headers()
    last_beat = time.monotonic()
    try:
        while True:
            with COND:
                evs = [e for e in DB["events"] if e["run_id"] == rid and e["sequence"] > after]
                if not evs:
                    COND.wait(timeout=1.0)
                    evs = [e for e in DB["events"] if e["run_id"] == rid and e["sequence"] > after]
            for e in evs:
                h.wfile.write(f"id: {e['sequence']}\nevent: {e['event_type']}\ndata: {json.dumps(e, ensure_ascii=False)}\n\n".encode())
                after = e["sequence"]
            if time.monotonic() - last_beat > 15:
                h.wfile.write(b": heartbeat\n\n")
                last_beat = time.monotonic()
            h.wfile.flush()
    except (BrokenPipeError, ConnectionResetError):
        return None


@route("GET", "/runs/([A-Za-z0-9_\\-]+)/diff")
def run_diff(ctx, rid):
    run = visible_run(ctx, rid)
    if not run.get("validation"):
        raise ApiError(409, "NOT_VALIDATED", "No validation report yet.")
    mp = DB["mappings"][run["mapping_id"]]
    return 200, {"validation": run["validation"], "operations": run["plan"]["operations"], "mapping_sha256": mp["mapping_sha256"],
                 "plan_sha256": run["plan_sha256"], "policy_version": run["plan"]["policy_version"],
                 "base_sha256": run["plan"]["base_sha256"], "base_version_id": run["base_version_id"],
                 "candidate_sha256": run["candidate_sha256"]}


@route("POST", "/runs/([A-Za-z0-9_\\-]+)/corrections", idem=True)
def correct_run(ctx, rid):
    run, b = visible_run(ctx, rid), jbody(ctx)
    if run["state"] not in ("NEEDS_REVIEW",):
        raise ApiError(409, "STATE_CONFLICT", f"Run is {run['state']}; corrections need NEEDS_REVIEW.")
    if b.get("expected_run_revision") != run["revision"]:
        raise ApiError(409, "REVISION_CONFLICT", "The run changed; reload.", details={"revision": run["revision"]})
    corr = b.get("corrections") or {}
    allowed = {"merchant_name", "supplier_reference", "supplier_org_no", "document_date", "gross_minor", "net_minor", "tax_minor",
               "tax_rate_basis_points", "payment_status", "payment_source", "category_account_id", "tax_treatment", "kind",
               "acknowledge_security_flag"}
    if bad := set(corr) - allowed:
        raise ApiError(400, "UNSUPPORTED_FIELDS", f"Unknown correction fields: {sorted(bad)}")
    if ctx["session"]["role"] == "employee" and set(corr) & {"payment_source", "category_account_id", "tax_treatment"}:
        raise ApiError(403, "FORBIDDEN", "Only an accountant can set accounts, payment source or VAT treatment.")
    with LOCK:
        t = json.loads(json.dumps(run["transaction"]))
        t["revision"] += 1
        for k, v in corr.items():
            if k in ("acknowledge_security_flag", "tax_rate_basis_points") or t.get(k) == v:
                continue  # unchanged values keep their document evidence
            t[k] = v
            t["evidence"].append({"evidence_id": f"hc_{k}_{t['revision']}", "field": k, "source": "human_confirmation",
                                  "text": f"Set by {ctx['session']['display_name']}: {v}", "bbox": None, "page": 1, "status": "confirmed"})
        if t.get("net_minor") is not None and t.get("tax_minor") is not None:
            rate = corr.get("tax_rate_basis_points") or (t["tax_lines"][0]["rate_basis_points"] if t["tax_lines"] else None)
            t["tax_lines"] = [{"base_minor": t["net_minor"], "tax_minor": t["tax_minor"], "rate_basis_points": rate,
                               "source_evidence_ids": [e["evidence_id"] for e in t["evidence"] if e["field"] == "tax_minor"][:5] or ["none"]}]
        t["unresolved_fields"] = [f for f in t["unresolved_fields"] if f not in corr and t.get(f) in (None, "unknown")]
        t["confirmed_by"], t["confirmed_at"] = ctx["session"]["user_id"], now()
        run["transaction"] = t
        if corr.get("acknowledge_security_flag"):
            run["security_flags"] = []
        set_state(run, "QUEUED", "CORRECTED", f"Correction by {ctx['session']['display_name']}: {b.get('reason') or 'fields updated'}.")
    threading.Thread(target=lambda: _continue_after_review(rid), daemon=True).start()
    return 202, {"run_id": rid, "state": "QUEUED", "transaction_revision": t["revision"]}


def _continue_after_review(rid):
    try:
        with LOCK:
            run = DB["runs"][rid]
            if run["security_flags"]:
                set_state(run, "NEEDS_REVIEW", "SECURITY_REVIEW", "Security flag still open.")
                return
        plan_and_execute(rid)
    except Exception:  # noqa: BLE001
        traceback.print_exc()


@route("POST", "/runs/([A-Za-z0-9_\\-]+)/duplicate-resolution", roles=("accountant", "owner"), idem=True)
def resolve_duplicate(ctx, rid):
    run, b = visible_run(ctx, rid), jbody(ctx)
    if run["state"] != "DUPLICATE_REVIEW":
        raise ApiError(409, "STATE_CONFLICT", "Not held as a duplicate.")
    with LOCK:
        if b.get("decision") == "same_transaction":
            set_state(run, "REJECTED", "DUPLICATE_CONFIRMED", "Confirmed duplicate; nothing posted.")
        else:
            run["duplicate_resolution"] = "distinct_transaction"
            set_state(run, "QUEUED", "DISTINCT_CONFIRMED", "Confirmed as a distinct purchase.")
            threading.Thread(target=lambda: plan_and_execute(rid), daemon=True).start()
    return 200, snapshot(run, ctx["session"]["role"])


@route("POST", "/runs/([A-Za-z0-9_\\-]+)/cancel", idem=True)
def cancel_run(ctx, rid):
    run = visible_run(ctx, rid)
    if run["state"] in ("COMMITTED", "REJECTED", "FAILED", "CANCELLED", "EXPIRED", "STALE_BASE"):
        raise ApiError(409, "STATE_CONFLICT", f"Run is already {run['state']}.")
    with LOCK:
        set_state(run, "CANCELLED", "CANCELLED_BY_USER", "Cancelled.")
        emit(rid, "run.cancelled", "CANCELLED", "Cancelled by user.")
    return 202, snapshot(run, ctx["session"]["role"])


@route("POST", "/runs/([A-Za-z0-9_\\-]+)/approval", roles=("accountant", "owner"), idem=True)
def approve(ctx, rid):
    run, b = visible_run(ctx, rid), jbody(ctx)
    with LOCK:
        if run["state"] != "AWAITING_APPROVAL":
            if run["state"] == "COMMITTED":
                return 200, {"commit": run["commit"], "run": snapshot(run, ctx["session"]["role"])}
            raise ApiError(409, "STATE_CONFLICT", f"Run is {run['state']}, not awaiting approval.")
        if b.get("decision") == "reject":
            run["rejection"] = {"actor_id": ctx["session"]["user_id"], "comment": (b.get("comment") or "")[:500], "at": now()}
            set_state(run, "REJECTED", "REJECTED_BY_REVIEWER", f"Rejected: {b.get('comment') or 'no reason given'}")
            return 200, {"commit": None, "run": snapshot(run, ctx["session"]["role"])}
        mp = DB["mappings"][run["mapping_id"]]
        want = {"base_version_id": run["base_version_id"], "base_sha256": run["plan"]["base_sha256"],
                "candidate_sha256": run["candidate_sha256"], "plan_sha256": run["plan_sha256"], "mapping_sha256": mp["mapping_sha256"],
                "validation_report_sha256": run["validation"]["report_sha256"], "policy_version": run["plan"]["policy_version"]}
        mism = [k for k, v in want.items() if b.get(k) != v]
        if mism:
            raise ApiError(409, "APPROVAL_HASH_MISMATCH", "What you reviewed is not what would be committed. Reload.",
                           details={"mismatched": mism})
        wb = DB["workbooks"][run["workbook_id"]]
        if wb["current_version_id"] != run["base_version_id"]:
            set_state(run, "STALE_BASE", "STALE_BASE", "The workbook changed after this preview. Create a new run.")
            raise ApiError(409, "STALE_BASE", "This workbook changed after the preview. Create a new run and approve its result.",
                           details={"current_version_id": wb["current_version_id"]})
        cand = DB["artifacts"][run["candidate_artifact_id"]]["bytes"]
        if sha(cand) != run["candidate_sha256"]:
            raise ApiError(409, "APPROVAL_HASH_MISMATCH", "Candidate bytes changed.")
        set_state(run, "COMMITTING", "APPROVED", f"Approved by {ctx['session']['display_name']}.")
        vid = oid("ver")
        art = put_artifact(cand, f"{wb['display_name']}_v{len(wb['versions']) + 1}.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        commit = {"commit_id": oid("cmt"), "approval_id": oid("apr"), "run_id": rid, "workbook_id": wb["workbook_id"],
                  "previous_version_id": wb["current_version_id"], "version_id": vid, "artifact_id": art, "artifact_sha256": sha(cand),
                  "transaction_id": run["transaction"]["transaction_id"], "transaction_revision": run["transaction"]["revision"],
                  "committed_by": ctx["session"]["user_id"], "committed_at": now()}
        DB["versions"][vid] = {"version_id": vid, "workbook_id": wb["workbook_id"], "sha256": sha(cand), "artifact_id": art,
                               "created_at": now(), "source": "commit", "commit_id": commit["commit_id"], "run_id": rid}
        wb["versions"].append(vid)
        wb["current_version_id"] = vid
        audit = [e for e in DB["events"] if e["run_id"] == rid]
        commit["audit_artifact_id"] = put_artifact(json.dumps({"commit": commit, "transaction": run["transaction"], "entry": run["entry"],
                                                               "validation": run["validation"], "events": audit}, indent=1,
                                                              ensure_ascii=False).encode(), f"ledgerflow_audit_{rid}.json", "application/json")
        run["commit"] = commit
        set_state(run, "COMMITTED", "COMMITTED", f"Committed as version {len(wb['versions'])}.")
        emit(rid, "commit.completed", "COMMITTED", "Workbook version committed.",
             {"commit_id": commit["commit_id"], "version_id": vid, "artifact_sha256": commit["artifact_sha256"]})
        if run["transaction"]["payment_status"] == "unpaid":
            DB["open_items"].append({"open_item_id": oid("oi"), "supplier_name": run["transaction"]["merchant_name"],
                                     "reference": run["transaction"]["supplier_reference"], "gross_minor": run["transaction"]["gross_minor"],
                                     "status": "open", "run_id": rid})
        for other in DB["runs"].values():  # proactively mark previews of the old version stale (Codex: terminal STALE_BASE)
            if other is not run and other["workbook_id"] == wb["workbook_id"] and other["state"] == "AWAITING_APPROVAL":
                set_state(other, "STALE_BASE", "STALE_BASE", "Another entry was committed first. Re-run on the new version.")
    return 200, {"commit": commit, "run": snapshot(run, ctx["session"]["role"])}


@route("POST", "/runs/([A-Za-z0-9_\\-]+)/rerun", idem=True)
def rerun(ctx, rid):
    """Extension: fresh linked run for the same document on the current version (after STALE_BASE)."""
    old = visible_run(ctx, rid)
    if old["state"] not in ("STALE_BASE", "FAILED", "EXPIRED"):
        raise ApiError(409, "STATE_CONFLICT", "Only stale, failed or expired runs can be re-run.")
    wb = DB["workbooks"][old["workbook_id"]]
    ver = DB["versions"][wb["current_version_id"]]
    with LOCK:
        nid = oid("run")
        new = {**{k: old[k] for k in ("workbook_id", "document_id", "mapping_id", "mapping_version", "created_by", "mock_labels")},
               "run_id": nid, "revision": 0, "state": "QUEUED", "state_reason": "RERUN", "base_version_id": ver["version_id"],
               "attempt_count": 0, "last_event_sequence": 0, "transaction": old["transaction"], "entry": None, "plan_sha256": None,
               "validation_summary": None, "candidate_artifact_id": None, "candidate_sha256": None, "commit": None,
               "created_at": now(), "updated_at": now(), "rerun_of": rid, "security_flags": []}
        DB["runs"][nid] = new
        emit(nid, "run.created", "QUEUED", f"Re-run of {rid} on the current workbook version.", {"rerun_of": rid})
    threading.Thread(target=lambda: _run_safely(nid, "PLANNING"), daemon=True).start()
    return 202, {"run_id": nid, "state": "QUEUED", "events_url": f"/api/v1/runs/{nid}/events"}


@route("GET", "/artifacts/([A-Za-z0-9_\\-]+)/download")
def download(ctx, aid):
    a = get_or_404("artifacts", aid)
    h = ctx["handler"]
    h.send_response(200)
    h.send_header("Content-Type", a["content_type"])
    h.send_header("Content-Length", str(len(a["bytes"])))
    h.send_header("ETag", f"\"{a['sha256']}\"")
    if not a["content_type"].startswith("image/"):
        h.send_header("Content-Disposition", f"attachment; filename=\"{a['filename']}\"")
    h.end_headers()
    h.wfile.write(a["bytes"])
    return None


# ------------------------------------------------------------------ DEV MOCK only: sample files for demos/tests
@route("GET", "/dev/fixtures", auth=False)
def list_fixtures(ctx):
    cases = json.loads((FIXTURES / "cases.json").read_text())
    return 200, {"workbooks": ["nordvik_t_accounts.xlsx", "nordvik_t_accounts_error.xlsx"],
                 "receipts": [{"case_id": c["case_id"], "title": c["title"], "file": c["image"].split("/")[-1]} for c in cases]}


@route("GET", "/dev/fixtures/([A-Za-z0-9_.\\-]+)", auth=False)
def get_fixture(ctx, name):
    path = (FIXTURES / name) if name.endswith(".xlsx") else (FIXTURES / "receipts" / name)
    if not path.is_file() or path.resolve().parent not in (FIXTURES.resolve(), (FIXTURES / "receipts").resolve()):
        raise ApiError(404, "NOT_FOUND", "Unknown fixture.")
    data = path.read_bytes()
    h = ctx["handler"]
    h.send_response(200)
    h.send_header("Content-Type", "image/png" if name.endswith(".png") else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    h.send_header("Content-Length", str(len(data)))
    h.end_headers()
    h.wfile.write(data)
    return None


# ------------------------------------------------------------------ containment test (proposed extension)
@route("POST", "/containment-tests", roles=("accountant", "owner"), idem=True)
def containment_test(ctx):
    tid = oid("ctest")
    DB["containment"][tid] = {"test_id": tid, "state": "RUNNING", "started_at": now(), "lines": [], "result": None}

    def work():
        res = sandbox.run({"main.py": programs.CONTAINMENT_PROBE.encode()}, deadline_s=10)
        probes = [ln for ln in (res["stdout"] + res["stderr"]).splitlines() if ln.startswith("PROBE")]
        with LOCK:
            DB["containment"][tid].update(state="DONE", lines=probes, result={k: res[k] for k in (
                "runtime", "sandbox_id", "exit_code", "termination_reason", "duration_ms", "destroyed", "limits")}, finished_at=now())
            emit(None, "containment.observed", None, f"Containment test {tid}: {res['termination_reason']}",
                 {"test_id": tid, "termination_reason": res["termination_reason"], "destroyed": res["destroyed"]})
    threading.Thread(target=work, daemon=True).start()
    return 202, {"test_id": tid, "state": "RUNNING"}


@route("GET", "/benchmark/kpis", roles=("accountant", "owner"))
def benchmark_kpis(ctx):
    """Extension: measured KPIs (schema ledgerflow.kpis.v1) from benchmark/results/kpis.json, read at request time."""
    f = REPO / "benchmark" / "results" / "kpis.json"
    if not f.exists():
        raise ApiError(404, "NOT_FOUND", "No benchmark KPIs yet: run python3 benchmark/kpis.py.")
    return 200, json.loads(f.read_text(encoding="utf-8"))


@route("GET", "/containment-tests/([A-Za-z0-9_\\-]+)", roles=("accountant", "owner"))
def get_containment(ctx, tid):
    return 200, get_or_404("containment", tid)


def main():
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    srv.daemon_threads = True
    mode = (f"Vultr {vsi.MODEL} (reasoning_effort={vsi.REASONING_EFFORT or 'model default'}, codegen prompt {vsi.CODEGEN_PROMPT_VERSION})"
            if vsi.enabled() else "MOCK (no VULTR_INFERENCE_API_KEY)")
    print(f"LedgerFlow DEV MOCK API on http://localhost:{PORT}  (docker: {sandbox.docker_available()}, image: {sandbox.IMAGE}, inference: {mode})")
    srv.serve_forever()


if __name__ == "__main__":
    main()
