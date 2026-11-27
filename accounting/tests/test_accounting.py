"""Accounting rules + reference verifier tests. Run: python3 -m pytest accounting/tests -q"""
from __future__ import annotations

import copy
import io
import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "accounting"))

from ledgerflow_accounting import (Workbook, admit, admit_settlement, allocate, baseline, check_entry,  # noqa: E402
                                   detect_mapping, verify)
from ledgerflow_accounting.reference_writer import patch_cells  # noqa: E402

SYN = ROOT / "fixtures" / "synthetic"
PRIVATE_SSE = ROOT / "fixtures" / "private" / "sse_anonymized.xlsx"
CASES = {c["case_id"]: c for c in json.loads((SYN / "cases.json").read_text())}
needs_sse = pytest.mark.skipif(not PRIVATE_SSE.exists(), reason="private anonymized SSE fixture not built")


def run_pipeline(xlsx: bytes, txn: dict, **verify_kw):
    res = admit(txn)
    assert res["admitted"], res["review"]
    wb = Workbook(xlsx)
    mapping = detect_mapping(wb)
    plan = allocate(wb, mapping, res["entry"])
    plan["entry"] = res["entry"]
    writes = {o["cell"]: o["after"] for o in plan["operations"]}
    cand = patch_cells(xlsx, mapping["sheet"], writes)
    return plan, cand, verify(xlsx, cand, plan, transaction=txn, **verify_kw)


# ---------------------------------------------------------------- real workbook facts (product/WORKBOOK_ANALYSIS.md)
@needs_sse
def test_sse_mapping_matches_analysis():
    m = detect_mapping(Workbook(PRIVATE_SSE.read_bytes()))
    assert m["sheet"] == "T-Accounts" and len(m["accounts"]) == 32 and m["slot_count"] == 369
    a = m["accounts"]["1940"]
    assert a["debit"]["opening_balance_cell"] == "P8" and a["debit"]["writable_rows"][0] == 9
    assert a["credit"]["writable_rows"] == list(range(8, 21))
    assert m["accounts"]["2440"]["credit"]["opening_balance_cell"] == "C30"


@needs_sse
def test_sse_baseline_finds_the_g48_error():
    wb = Workbook(PRIVATE_SSE.read_bytes())
    b = baseline(wb, detect_mapping(wb))
    assert (b["debits_minor"], b["credits_minor"], b["difference_minor"]) == (190846500, 182048900, 8797600)
    assert b["opening_debits_minor"] == b["opening_credits_minor"] == 122000000
    assert {(e["account_id"], e["amount_cell"]) for e in b["contra_exceptions"]} == {("2730", "G48"), ("7510", "B76")}
    assert b["acknowledgement_required"]


@needs_sse
def test_sse_e1_allocates_exactly_the_spec_cells_and_verifies():
    plan, cand, rep = run_pipeline(PRIVATE_SSE.read_bytes(), CASES["E1"]["transaction"], cleanup_confirmed=True)
    cells = {o["cell"]: o["after"]["value"] for o in plan["operations"]}
    assert cells == {"K64": "[1940]", "L64": "1000", "K38": "[1940]", "L38": "250",
                     "R12": "[6110]", "S12": "1000", "R13": "[2640]", "S13": "250"}
    assert rep["result"] == "pass", [c for c in rep["checks"] if c["status"] != "pass"]
    assert rep["baseline"]["difference_minor"] == 8797600  # pre-existing gap unchanged, reported not fixed


# ---------------------------------------------------------------- synthetic workbook
def test_synthetic_workbook_detected_and_balanced():
    wb = Workbook((SYN / "nordvik_t_accounts.xlsx").read_bytes())
    m = detect_mapping(wb)
    b = baseline(wb, m)
    assert len(m["accounts"]) == 20 and b["difference_minor"] == 0 and not b["contra_exceptions"]
    assert b["opening_debits_minor"] == b["opening_credits_minor"] == 38300000


def test_synthetic_error_variant_flags_wrong_side_posting():
    wb = Workbook((SYN / "nordvik_t_accounts_error.xlsx").read_bytes())
    b = baseline(wb, detect_mapping(wb))
    assert b["difference_minor"] == 160000 and len(b["contra_exceptions"]) == 2


@pytest.mark.parametrize("case", ["E1", "E2", "B27"])
def test_synthetic_end_to_end_cases_pass(case):
    xlsx = (SYN / "nordvik_t_accounts.xlsx").read_bytes()
    _, _, rep = run_pipeline(xlsx, CASES[case]["transaction"], cleanup_confirmed=True)
    assert rep["result"] == "pass", [c for c in rep["checks"] if c["status"] != "pass"]


def test_without_cleanup_attestation_result_is_not_pass():
    _, _, rep = run_pipeline((SYN / "nordvik_t_accounts.xlsx").read_bytes(), CASES["E1"]["transaction"])
    assert rep["result"] == "review_required" and rep["not_passed_mandatory"] == ["cleanup_confirmed"]


def test_cash_purchase_reading_formula_precedents_is_not_silently_passed():
    txn = copy.deepcopy(CASES["E1"]["transaction"])
    txn["payment_source"] = "company_cash"
    _, _, rep = run_pipeline((SYN / "nordvik_t_accounts.xlsx").read_bytes(), txn, cleanup_confirmed=True)
    st = {c["check_id"]: c["status"] for c in rep["checks"]}
    assert st["formula_postings_stable"] == "not_performed" and rep["result"] == "review_required"


# ---------------------------------------------------------------- admission rules
def test_admit_e1_e2_entries():
    for cid in ("E1", "E2"):
        r = admit(CASES[cid]["transaction"])
        assert r["admitted"]
        got = [(ln["account_id"], ln["side"], ln["amount_minor"]) for ln in r["entry"]["lines"]]
        assert got == [tuple(x) for x in CASES[cid]["expected_entry"]]


def test_never_assume_payment():
    r = admit(CASES["B11"]["transaction"])
    assert not r["admitted"] and "PAYMENT_CONTEXT_REQUIRED" in {x["code"] for x in r["review"]}


def test_inconsistent_totals_go_to_review():
    codes = {x["code"] for x in admit(CASES["B12"]["transaction"])["review"]}
    assert {"AMOUNTS_INCONSISTENT", "TAX_REVIEW_REQUIRED"} <= codes


@pytest.mark.parametrize("change,code", [
    ({"currency": "EUR"}, "CURRENCY_UNSUPPORTED"),
    ({"document_date": "2025-06-01"}, "PERIOD_CLOSED"),
    ({"supplier_org_no": None}, "TAX_REVIEW_REQUIRED"),
    ({"category_account_id": "3001"}, "ACCOUNT_REVIEW_REQUIRED"),
    ({"payment_source": "employee_personal"}, "PAYMENT_CONTEXT_REQUIRED"),
    ({"tax_treatment": "unknown"}, "TAX_REVIEW_REQUIRED"),
    ({"tax_lines": [{"base_minor": 100000, "tax_minor": 25000, "rate_basis_points": 2000, "source_evidence_ids": ["e1_tax_minor"]}]},
     "TAX_REVIEW_REQUIRED"),
    ({"evidence": []}, "EVIDENCE_MISSING"),
])
def test_review_triggers(change, code):
    txn = {**copy.deepcopy(CASES["E1"]["transaction"]), **change}
    r = admit(txn)
    assert not r["admitted"] and code in {x["code"] for x in r["review"]}, r["review"]


def test_large_receipt_without_invoice_number_cannot_deduct():
    txn = {**copy.deepcopy(CASES["E1"]["transaction"]), "gross_minor": 625000, "net_minor": 500000, "tax_minor": 125000,
           "supplier_reference": None,
           "tax_lines": [{"base_minor": 500000, "tax_minor": 125000, "rate_basis_points": 2500, "source_evidence_ids": ["e1_tax_minor"]}]}
    assert "supplier_reference" in {x["field"] for x in admit(txn)["review"]}


def test_nondeductible_posts_gross_without_vat_line():
    txn = {**copy.deepcopy(CASES["E1"]["transaction"]), "tax_treatment": "configured_nondeductible"}
    r = admit(txn)
    assert [(ln["account_id"], ln["amount_minor"]) for ln in r["entry"]["lines"]] == [("6110", 125000), ("1940", 125000)]


def test_settlement_matches_open_invoice_and_refuses_ambiguity():
    items = [{"open_item_id": "oi_1", "supplier_name": "Molnverk AB", "reference": "2026-1187", "ocr": "20261187",
              "gross_minor": 500000, "status": "open"}]
    pay = {"transaction_id": "txn_e3", "revision": 1, "date": "2026-11-27", "amount_minor": 500000, "reference": "20261187",
           "supplier_name": "Molnverk AB", "evidence_ids": ["e3_amount"]}
    r = admit_settlement(pay, items)
    assert r["admitted"] and [(x["account_id"], x["side"]) for x in r["entry"]["lines"]] == [("2440", "debit"), ("1940", "credit")]
    assert all(c["status"] == "pass" for c in check_entry(r["entry"], {}, settlement=True))
    assert not admit_settlement({**pay, "amount_minor": 510000, "reference": None}, items)["admitted"]
    assert not admit_settlement(pay, items + [dict(items[0], open_item_id="oi_2")])["admitted"]


# ---------------------------------------------------------------- negative verifier cases (product/BENCHMARKS.md B-21..B-26)
@pytest.fixture
def e1_synthetic():
    xlsx = (SYN / "nordvik_t_accounts.xlsx").read_bytes()
    plan, cand, _ = run_pipeline(xlsx, CASES["E1"]["transaction"], cleanup_confirmed=True)
    return xlsx, plan, cand


def _status(rep):
    return {c["check_id"]: c["status"] for c in rep["checks"]}


def _rewrite(xlsx: bytes, part: str, fn) -> bytes:
    src, out = zipfile.ZipFile(io.BytesIO(xlsx)), io.BytesIO()
    with zipfile.ZipFile(out, "w") as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            dst.writestr(info, fn(data) if info.filename == part else data)
    return out.getvalue()


def test_b21_openpyxl_save_is_rejected(e1_synthetic, tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    xlsx, plan, _ = e1_synthetic
    p = tmp_path / "x.xlsx"
    p.write_bytes(xlsx)
    wb = openpyxl.load_workbook(p)
    for o in plan["operations"]:
        v = o["after"]["value"]
        wb["T-Accounts"][o["cell"]] = v if o["after"]["type"] == "text" else float(v)
    wb.save(p)
    rep = verify(xlsx, p.read_bytes(), plan, cleanup_confirmed=True)
    assert rep["result"] == "fail" and _status(rep)["features_preserved"] == "fail"


def test_b22_extra_formula_edit_is_rejected(e1_synthetic):
    xlsx, plan, cand = e1_synthetic
    bad = _rewrite(cand, "xl/worksheets/sheet2.xml", lambda d: d.replace(b"<f>SUM(", b"<f>1+SUM(", 1))
    st = _status(verify(xlsx, bad, plan, cleanup_confirmed=True))
    assert st["formulas_unchanged"] == "fail" and st["non_target_cells_unchanged"] == "fail"


def test_b23_write_into_opening_balance_row_is_rejected(e1_synthetic):
    xlsx, plan, _ = e1_synthetic
    plan = copy.deepcopy(plan)
    ob_cell = "Q6"  # 1940 debit [OB] amount cell in the synthetic grid
    plan["operations"].append({"sheet": "T-Accounts", "cell": ob_cell, "before": {}, "after": {"type": "number", "value": "1"},
                               "line_id": "line_credit", "allocation_id": "alloc_x", "role": "debit_amount"})
    st = _status(verify(xlsx, xlsx, plan, cleanup_confirmed=True))
    assert st["source_preconditions"] == "fail"


def test_b24_reference_written_as_number_is_rejected(e1_synthetic):
    xlsx, plan, _ = e1_synthetic
    ref = next(o for o in plan["operations"] if o["role"] == "debit_reference")
    writes = {o["cell"]: o["after"] for o in plan["operations"]}
    writes[ref["cell"]] = {"type": "number", "value": "1940"}
    cand = patch_cells(xlsx, "T-Accounts", writes)
    rep = verify(xlsx, cand, plan, cleanup_confirmed=True)
    assert rep["result"] == "fail" and _status(rep)["exact_write_set"] == "fail"


def test_b25_half_posted_entry_is_rejected(e1_synthetic):
    xlsx, plan, _ = e1_synthetic
    writes = {o["cell"]: o["after"] for o in plan["operations"] if o["role"].startswith("debit")}
    cand = patch_cells(xlsx, "T-Accounts", writes)
    st = _status(verify(xlsx, cand, plan, cleanup_confirmed=True))
    assert st["exact_write_set"] == "fail" and st["account_allocation"] == "fail"


def test_b26_balanced_phantom_payable_is_rejected():
    txn = CASES["E1"]["transaction"]
    entry = copy.deepcopy(admit(txn)["entry"])
    entry["lines"][-1]["account_id"] = "2440"  # paid by card but credited to payables: still balanced
    st = {c["check_id"]: c["status"] for c in check_entry(entry, txn)}
    assert st["V-BAL-01"] == "pass" and st["V-SEM-03"] == "fail"


def test_package_with_a_missing_sheet_part_is_refused_not_crashed(e1_synthetic):
    """Found by the benchmark (F11): the verifier used to raise KeyError on a package missing a listed sheet."""
    xlsx, plan, cand = e1_synthetic
    txn = CASES["E1"]["transaction"]
    src = zipfile.ZipFile(io.BytesIO(cand))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for i in src.infolist():
            if i.filename != "xl/worksheets/sheet1.xml":
                z.writestr(i, src.read(i.filename))
    rep = verify(xlsx, buf.getvalue(), plan, transaction=txn, cleanup_confirmed=True)
    assert rep["result"] == "fail" and rep["checks"][0]["check_id"] == "archive_safe"


def test_above_4000_sek_warns_about_full_invoice_fields():
    """Kvittion spec: warn above SEK 4,000 when buyer details are not established (non-blocking; entry unchanged)."""
    txn = copy.deepcopy(CASES["E2"]["transaction"])  # 5,000 SEK supplier invoice
    res = admit(txn)
    assert res["admitted"] and any("Above SEK 4,000" in a for a in res["advisories"])
    small = admit(copy.deepcopy(CASES["E1"]["transaction"]))  # 1,250 SEK
    assert not any("Above SEK 4,000" in a for a in small["advisories"])
