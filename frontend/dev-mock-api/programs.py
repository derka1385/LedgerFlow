"""Programs executed in the sandbox by the DEV MOCK API.

MOCK_GENERATED_PROGRAM stands in for model-generated code: there are no Vultr
credentials yet, so the mock "code generation" step returns this template and
labels it model_id="MOCK_CODEGEN_TEMPLATE". The real path asks Vultr Serverless
Inference for the program (product/PROMPTS.md, call 3). Everything after that
(sandbox, verifier, approval) is real.
"""
from __future__ import annotations

from pathlib import Path

ACCOUNTING = Path(__file__).resolve().parents[2] / "accounting" / "ledgerflow_accounting"

MOCK_GENERATED_PROGRAM = r'''# MOCK_CODEGEN_TEMPLATE: stands in for model-generated code (no Vultr credentials yet)
import hashlib, json, sys
from ledgerflow_workbook import Workbook, patch_cells

plan = json.load(open("/input/plan.json"))
src = open("/input/source.xlsx", "rb").read()
print(f"source sha256 {hashlib.sha256(src).hexdigest()[:16]}... ({len(src)} bytes)")
if hashlib.sha256(src).hexdigest() != plan["base_sha256"]:
    sys.exit("source bytes do not match plan base_sha256")
ops = plan["operations"]
sheet = ops[0]["sheet"]
wb = Workbook(src)
cells = wb.cells(sheet)
for op in ops:  # 1. inspect: every target must still be blank
    if op["cell"] in cells:
        print(f"precondition failed: {sheet}!{op['cell']} is not blank", file=sys.stderr)
        sys.exit(2)
print(f"inspected {len(ops)} target cells on {sheet!r}: all blank")
writes = {op["cell"]: op["after"] for op in ops}
out = patch_cells(src, sheet, writes)  # 2. write (no openpyxl save: it drops data validations)
after = Workbook(out).cells(sheet)  # 3. self-check by re-reading the output
bad = [c for c, a in writes.items() if c not in after or str(after[c].value) != str(a["value"])]
if bad:
    print(f"self-check failed for {bad}", file=sys.stderr)
    sys.exit(2)
for op in ops:
    print(f"  wrote {sheet}!{op['cell']:<5} {op['after']['value']:>10}  ({op['role']}, {op['line_id']})")
open("/work/candidate.xlsx", "wb").write(out)
json.dump({"written": sorted(writes), "self_check": {"ok": True}}, open("/work/report.json", "w"))
print(f"candidate written: {len(out)} bytes, sha256 {hashlib.sha256(out).hexdigest()[:16]}...")
'''

CONTAINMENT_PROBE = r'''# Fixed hostile probe (not model-generated): proves the sandbox boundary
import os, socket, sys
print("PROBE env_names:", sorted(os.environ))
print("PROBE run_secrets_exists:", os.path.exists("/run/secrets"))
try:
    socket.create_connection(("198.51.100.7", 80), timeout=3); print("PROBE network: CONNECTED (BOUNDARY FAILED)")
except Exception as e:
    print("PROBE network:", type(e).__name__, e)
for p in ("/etc/ledgerflow_probe", "/input/overwrite_attempt"):
    try:
        open(p, "w").write("x"); print("PROBE filesystem", p, ": WRITTEN (BOUNDARY FAILED)")
    except Exception as e:
        print("PROBE filesystem", p, ":", type(e).__name__, e)
print("PROBE infinite_loop: starting (expect the host to kill this)")
sys.stdout.flush()
while True:
    pass
'''


def helper_package() -> dict[str, bytes]:
    """The sandbox helper `ledgerflow_workbook` = reference reader + writer (stands in for Codex's helper)."""
    files = {
        "ledgerflow_workbook/__init__.py": b"from .ooxml import Workbook, WorkbookError\nfrom .reference_writer import patch_cells\n",
        "ledgerflow_workbook/ooxml.py": (ACCOUNTING / "ooxml.py").read_bytes(),
        "ledgerflow_workbook/reference_writer.py": (ACCOUNTING / "reference_writer.py").read_bytes(),
    }
    return files
