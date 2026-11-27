"""The real-inference path, against a local OpenAI-compatible fake of Vultr Serverless Inference.

Proves the wiring that switches on with VULTR_INFERENCE_API_KEY: structured-output fallback
(json_schema rejected -> json_object), extraction -> TransactionV1, account proposal,
code generation, static screen refusing a hostile first program, repair hint, real
Docker sandbox, verifier, approval. Needs Docker; skips otherwise.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import programs  # noqa: E402
import sandbox  # noqa: E402
import test_mock_api as T  # noqa: E402

pytestmark = pytest.mark.skipif(not (sandbox.docker_available() and sandbox.image_available()),
                                reason=f"Docker or image {sandbox.IMAGE} unavailable")

FACT = lambda v, q: {"status": "known", "value": v, "quote": q}  # noqa: E731
UNK = {"status": "unknown", "value": None, "quote": None}
EXTRACTION = {
    "document_kind": FACT("receipt", "KVITTO"), "supplier_name": FACT("Pappershörnan AB", "PAPPERSHÖRNAN AB"),
    "supplier_org_no": FACT("559999-0303", "Org.nr 559999-0303"), "document_date": FACT("2026-11-27", "2026-11-27 08:15"),
    "document_number": FACT("P-1001", "Kvitto P-1001"), "due_date": UNK, "currency": FACT("SEK", "SEK"),
    "gross": FACT("62.50", "TOTALT 62,50"), "net": FACT("50.00", "Netto 50,00"), "vat": FACT("12.50", "Moms 25% 12,50"),
    "vat_rate": FACT("0.25", "Moms 25%"), "payment_method": FACT("card", "KORT ****4821"), "payment_status": FACT("paid", "GODKÄNT"),
    "card_last4": FACT("4821", "****4821"), "description": FACT("Pennor", "PENNOR 10-PACK"),
    "embedded_instructions_detected": False, "legibility": "good", "notes": "",
}
HOSTILE = "import socket\nsocket.create_connection(('198.51.100.7', 80))\n"


class Fake(BaseHTTPRequestHandler):
    calls: list = []
    codegen_count = 0

    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert self.headers["Authorization"] == "Bearer test-key"
        Fake.calls.append(body)
        rf = (body.get("response_format") or {}).get("type")
        system = body["messages"][0]["content"]
        if rf == "json_schema":  # pretend this model rejects json_schema: adapter must fall back
            self._send(400, {"error": {"message": "response_format json_schema not supported"}})
            return
        if "receipts" in system:
            content = json.dumps(EXTRACTION)
        elif "classify" in system:
            content = json.dumps({"proposed_account": "6110", "alternatives": [], "rationale": "Pens are office supplies (PENNOR 10-PACK)."})
        else:
            Fake.codegen_count += 1
            code = HOSTILE if Fake.codegen_count == 1 else programs.MOCK_GENERATED_PROGRAM
            content = f"Here is the program:\n```python\n{code}```"
        self._send(200, {"id": f"req_{len(Fake.calls)}", "choices": [{"message": {"role": "assistant", "content": content}}],
                         "usage": {"prompt_tokens": 100, "completion_tokens": 50}})

    def _send(self, status, obj):
        data = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture(scope="module")
def stack():
    fake = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=fake.serve_forever, daemon=True).start()
    port = T.free_port()
    env = {**os.environ, "PORT": str(port), "VULTR_INFERENCE_API_KEY": "test-key", "LEDGERFLOW_VSI_MODEL": "fake-vision-1",
           "VULTR_INFERENCE_BASE_URL": f"http://127.0.0.1:{fake.server_port}/v1"}
    proc = subprocess.Popen([sys.executable, str(HERE / "server.py")], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            urllib.request.urlopen(url + "/api/v1/health/live", timeout=1)
            break
        except OSError:
            time.sleep(0.2)
    yield url
    proc.terminate()
    fake.shutdown()


def test_real_inference_path_end_to_end(stack, tmp_path):
    owner, _ = T.onboard(stack)
    acct = T.Client(stack)
    s = acct.login("accountant-demo")
    assert s["inference"] == "vultr"
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (900, 400), "white")
    ImageDraw.Draw(img).text((20, 20), "PAPPERSHORNAN AB  TOTALT 62,50  (not a fixture)", fill="black")
    p = tmp_path / "new_receipt.png"
    img.save(p)
    st, targets, _ = acct.req("GET", "/upload-targets")
    t = targets["items"][0]
    st, doc, _ = acct.req("POST", f"/workbooks/{t['workbook_id']}/documents", files={"file": ("new.png", p.read_bytes())},
                          fields={"client_upload_id": "vsi_test"})
    st, run, _ = acct.req("POST", "/runs", {"workbook_id": t["workbook_id"], "document_id": doc["document_id"],
                                             "expected_base_version_id": t["base_version_id"], "expected_base_sha256": t["base_sha256"],
                                             "mapping_id": t["mapping_id"], "mapping_version": t["mapping_version"]})
    snap = T.wait_state(acct, run["run_id"], {"AWAITING_APPROVAL", "FAILED", "NEEDS_REVIEW"})
    assert snap["state"] == "AWAITING_APPROVAL", (snap["state"], snap["state_reason"], snap.get("review_items"))
    assert snap["mock_labels"] == [] and snap["attempt_count"] == 2
    assert [(ln["account_id"], ln["side"], ln["amount_minor"]) for ln in snap["entry"]["lines"]] == \
        [("6110", "debit", 5000), ("2640", "debit", 1250), ("1940", "credit", 6250)]
    events = T.read_sse(stack, acct, run["run_id"])
    ext = next(e for e in events if e["event_type"] == "extraction.completed")
    assert ext["data"]["mock"] is False and ext["data"]["mode"] == "json_object" and ext["data"]["model_id"] == "fake-vision-1"
    denied = [e for e in events if e["event_type"] == "containment.observed"]
    assert denied and "socket" in denied[0]["message"]
    gens = [e for e in events if e["event_type"] == "code.generated"]
    assert [g["data"]["model_id"] for g in gens] == ["fake-vision-1", "fake-vision-1"]
    # the repair request carried the refusal reason back to the model
    last_codegen = [c for c in Fake.calls if "sandbox" in c["messages"][0]["content"]][-1]
    assert "Static screen refused" in last_codegen["messages"][-1]["content"]
    # the API key never reached the sandbox: it is only in the host-side Authorization header
    assert all("test-key" not in json.dumps(c) for c in Fake.calls)
    assert acct.req("POST", f"/runs/{run['run_id']}/approval", T.approval_body(acct, run["run_id"]))[0] == 200
