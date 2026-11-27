"""Reference independent verifier for t_accounts candidates.

verify(base, candidate, plan, ...) reads the ACTUAL bytes of both files and
returns a ValidationReportV1-shaped dict (docs/DATA_SCHEMAS.md) using Codex's
mandatory check IDs, plus the product's T-account checks (V-TA-02/03/04).
No LLM, no openpyxl, no trust in anything the generated program reported.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

from .checks import check as entry_checks
from .ooxml import Workbook, WorkbookError, col_to_num, split_cell
from .tacc import baseline, contra_exceptions, detect_mapping, parse_lines, to_minor, trial_balance

VERIFIER_VERSION = "ledgerflow-accounting-verifier 0.1.0"
MANDATORY = ["archive_safe", "exact_write_set", "source_preconditions", "account_allocation", "new_entry_balanced",
             "non_target_cells_unchanged", "formulas_unchanged", "formula_postings_stable", "features_preserved",
             "no_new_active_content", "artifact_hash_match", "cleanup_confirmed"]
ACTIVE_CONTENT = re.compile(r"(vbaProject|externalLink|activeX|oleObject|embeddings/|customUI)", re.I)
RANGE_RE = re.compile(r"\$?([A-Z]{1,3})\$?(\d+)(?::\$?([A-Z]{1,3})\$?(\d+))?")


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _chk(cid: str, status: str, detail: str, expected=None, observed=None) -> dict:
    return {"check_id": cid, "status": status, "expected": None if expected is None else str(expected)[:200],
            "observed": None if observed is None else str(observed)[:200], "detail": detail[:500]}


def _in_range(cell: str, rng: tuple) -> bool:
    c1, r1, c2, r2 = rng
    col, row = split_cell(cell)
    c2, r2 = c2 or c1, int(r2 or r1)
    return col_to_num(c1) <= col_to_num(col) <= col_to_num(c2) and int(r1) <= row <= r2


def verify(base: bytes, candidate: bytes, plan: dict, *, transaction: dict | None = None, policy: dict | None = None,
           expected_candidate_sha256: str | None = None, cleanup_confirmed: bool | None = None,
           settlement: bool = False) -> dict:
    checks: list[dict] = []
    limitations = ["Native Excel recalculation not performed; formula values are cached values."]
    try:
        bwb, cwb = Workbook(base), Workbook(candidate)
        bad = [p for p in cwb.part_names if ACTIVE_CONTENT.search(p)]
        checks.append(_chk("archive_safe", "pass", "Candidate is a bounded, readable xlsx package."))
    except WorkbookError as exc:
        checks.append(_chk("archive_safe", "fail", f"{exc.code}: {exc}"))
        return _report(checks, [], {}, {}, limitations, base, candidate, plan, cleanup_confirmed)

    mapping = detect_mapping(bwb)
    sheet = mapping["sheet"]
    ops = plan["operations"]
    op_cells = {o["cell"]: o for o in ops}

    # --- package-level preservation --------------------------------------
    names_equal = bwb.part_names == cwb.part_names
    changed_parts = [n for n in bwb.part_names if n in cwb.part_names and bwb.read(n) != cwb.read(n)]
    ledger_part = bwb.sheets[sheet]
    other_changed = [p for p in changed_parts if p != ledger_part]
    dv_same = bwb.validation_sqrefs() == cwb.validation_sqrefs()
    checks.append(_chk("features_preserved", "pass" if names_equal and not other_changed and dv_same else "fail",
                       f"Zip entries identical in name/order: {names_equal}; parts changed besides the ledger sheet: "
                       f"{other_changed or 'none'}; data-validation ranges identical: {dv_same} "
                       f"({len(bwb.validation_sqrefs())} ranges).",
                       "only " + ledger_part, changed_parts))
    new_active = [p for p in bad if p not in bwb.part_names]
    checks.append(_chk("no_new_active_content", "pass" if not new_active else "fail",
                       f"New macro/external/embedded parts: {new_active or 'none'}."))

    # --- cell-level diff ---------------------------------------------------
    diffs, outside = [], []
    for name in bwb.sheets:
        bc, cc = bwb.cells(name), cwb.cells(name)
        bs, cs = bwb.style_ids(name), cwb.style_ids(name)
        for ref in sorted(set(bc) | set(cc) | (set(bs) ^ set(cs)), key=lambda r: (split_cell(r)[1], col_to_num(split_cell(r)[0]))):
            b, c = bc.get(ref), cc.get(ref)
            bd = b.as_dict() if b else {"type": "blank", "value": None, "formula": None, "style_id": bs.get(ref)}
            cd = c.as_dict() if c else {"type": "blank", "value": None, "formula": None, "style_id": cs.get(ref)}
            bd["style_id"], cd["style_id"] = bs.get(ref), cs.get(ref)
            if bd == cd:
                continue
            if name == sheet and ref in op_cells:
                diffs.append((ref, bd, cd))
            else:
                outside.append({"sheet": name, "cell": ref, "before": bd, "after": cd})
    checks.append(_chk("non_target_cells_unchanged", "pass" if not outside else "fail",
                       f"Cells changed outside the plan: {[o['sheet'] + '!' + o['cell'] for o in outside][:20] or 'none'}."))

    mism = []
    for ref, bd, cd in diffs:
        want = op_cells[ref]["after"]
        if cd["type"] != want["type"] or str(cd["value"]) != str(want["value"]) or cd["style_id"] != bd["style_id"]:
            mism.append(ref)
    missing = sorted(set(op_cells) - {d[0] for d in diffs})
    checks.append(_chk("exact_write_set", "pass" if not mism and not missing and not outside else "fail",
                       f"{len(diffs)} planned cells written; wrong value/type/style: {mism or 'none'}; not written: {missing or 'none'}.",
                       len(op_cells), len(diffs)))

    # --- preconditions against the mapping ---------------------------------
    pre_bad = []
    bcells = bwb.cells(sheet)
    for o in ops:
        if bcells.get(o["cell"]) is not None:
            pre_bad.append(f"{o['cell']} not blank in base")
            continue
        col, row = split_cell(o["cell"])
        ok = False
        for acc in mapping["accounts"].values():
            for side in ("debit", "credit"):
                s = acc[side]
                if row in s["writable_rows"] and col in (s["reference_column"], s["amount_column"]) and o["role"].startswith(side):
                    ok = True
        if not ok:
            pre_bad.append(f"{o['cell']} not a mapped {o['role']} slot")
    checks.append(_chk("source_preconditions", "pass" if not pre_bad else "fail",
                       f"Targets blank in base and inside mapped writable slots: {pre_bad or 'all ok'}."))

    bform = {r: c.formula for r, c in bcells.items() if c.type == "formula"}
    cform = {r: c.formula for r, c in cwb.cells(sheet).items() if c.type == "formula"}
    checks.append(_chk("formulas_unchanged", "pass" if bform == cform else "fail", f"{len(bform)} formulas compared on {sheet}."))
    touched = [(r, f) for r, f in bform.items()
               if any(_in_range(w, m) for m in RANGE_RE.findall(f or "") for w in op_cells)]
    checks.append(_chk("formula_postings_stable", "pass" if not touched else "not_performed",
                       "No formula reads a written cell." if not touched else
                       f"Formulas read written cells and need recalculation: {[t[0] for t in touched]}."))

    # --- accounting on the parsed workbooks --------------------------------
    entry = plan["entry"]
    blines, _ = parse_lines(bwb, mapping)
    clines, canom = parse_lines(cwb, mapping)
    btb, ctb = trial_balance(blines), trial_balance(clines)
    deltas = {}
    for acc in sorted(set(btb["accounts"]) | set(ctb["accounts"])):
        b = btb["accounts"].get(acc, {"debit_minor": 0, "credit_minor": 0})
        c = ctb["accounts"].get(acc, {"debit_minor": 0, "credit_minor": 0})
        d = {"debit_minor": c["debit_minor"] - b["debit_minor"], "credit_minor": c["credit_minor"] - b["credit_minor"]}
        if d["debit_minor"] or d["credit_minor"]:
            deltas[acc] = d
    want = {}
    for ln in entry["lines"]:
        w = want.setdefault(ln["account_id"], {"debit_minor": 0, "credit_minor": 0})
        w[f"{ln['side']}_minor"] += ln["amount_minor"]
    mirror_bad = []
    for a in plan["posting_allocations"]:
        dl = next(ln for ln in entry["lines"] if ln["line_id"] == a["debit_line_id"])
        cl = next(ln for ln in entry["lines"] if ln["line_id"] == a["credit_line_id"])
        ccells = cwb.cells(sheet)
        dref, damt = (ccells.get(x["cell"]) for x in a["debit_cells"])
        cref, camt = (ccells.get(x["cell"]) for x in a["credit_cells"])
        if not (dref and damt and cref and camt and dref.value == f"[{cl['account_id']}]" and cref.value == f"[{dl['account_id']}]"
                and to_minor(damt.value) == to_minor(camt.value) == a["amount_minor"]):
            mirror_bad.append(a["allocation_id"])
    new_exc = len(contra_exceptions(clines)) - len(contra_exceptions(blines))
    alloc_ok = deltas == want and not mirror_bad and new_exc <= 0 and not canom
    checks.append(_chk("account_allocation", "pass" if alloc_ok else "fail",
                       f"Trial-balance delta equals the entry: {deltas == want}; legs mirrored with reciprocal references "
                       f"(V-TA-02): {not mirror_bad}; new unreconciled lines (V-TA-03): {max(new_exc, 0)}; new anomalies: {len(canom)}.",
                       want, deltas))
    ed = sum(x["amount_minor"] for x in entry["lines"] if x["side"] == "debit")
    ec = sum(x["amount_minor"] for x in entry["lines"] if x["side"] == "credit")
    dd = sum(v["debit_minor"] for v in deltas.values())
    dc = sum(v["credit_minor"] for v in deltas.values())
    checks.append(_chk("new_entry_balanced", "pass" if ed == ec and dd == dc == ed else "fail",
                       f"Entry {ed}/{ec} öre; posted delta {dd}/{dc} öre.", ed, f"{dd}/{dc}"))

    cand_hash = sha256(candidate)
    if expected_candidate_sha256 is None:
        checks.append(_chk("artifact_hash_match", "pass", "Hash recorded for approval binding.", None, cand_hash))
    else:
        checks.append(_chk("artifact_hash_match", "pass" if cand_hash == expected_candidate_sha256 else "fail",
                           "Candidate bytes match the frozen hash.", expected_candidate_sha256, cand_hash))
    checks.append(_chk("cleanup_confirmed", {True: "pass", False: "fail", None: "not_performed"}[cleanup_confirmed],
                       "Host attestation that every isolated job was destroyed." if cleanup_confirmed is not None
                       else "Requires host lifecycle attestation (sandbox supervisor)."))
    if transaction is not None or settlement:
        checks.extend(entry_checks(entry, transaction or {}, policy, settlement=settlement))

    cell_diff = [{"sheet": sheet, "cell": ref, "before": bd, "after": cd,
                  "account_id": _account_for(mapping, ref), "side": op_cells[ref]["role"].split("_")[0],
                  "amount_delta_minor": to_minor(cd["value"]) if op_cells[ref]["role"].endswith("amount") else None,
                  "line_id": op_cells[ref]["line_id"], "allocation_id": op_cells[ref]["allocation_id"],
                  "reason": op_cells[ref]["role"]} for ref, bd, cd in diffs]
    base_report = baseline(bwb, mapping)
    return _report(checks, cell_diff, deltas, base_report, limitations, base, candidate, plan, cleanup_confirmed)


def _account_for(mapping: dict, ref: str) -> str | None:
    col, row = split_cell(ref)
    for code, acc in mapping["accounts"].items():
        for side in ("debit", "credit"):
            s = acc[side]
            if row in s["writable_rows"] and col in (s["reference_column"], s["amount_column"]):
                return code
    return None


def _report(checks, cell_diff, deltas, base_report, limitations, base, candidate, plan, cleanup) -> dict:
    statuses = {c["check_id"]: c["status"] for c in checks}
    failed = [c for c in checks if c["status"] == "fail"]
    pending = [m for m in MANDATORY if statuses.get(m) != "pass"]
    result = "fail" if failed else ("pass" if not pending else "review_required")
    return {
        "schema_version": "ledgerflow.validation.v1",
        "verifier_version": VERIFIER_VERSION,
        "base_sha256": sha256(base),
        "candidate_sha256": sha256(candidate),
        "result": result,
        "checks": checks,
        "cell_diff": cell_diff,
        "metadata_diff": [],
        "account_deltas": [{"account_id": a, "currency": "SEK", **v} for a, v in deltas.items()],
        "baseline": {k: base_report.get(k) for k in ("debits_minor", "credits_minor", "difference_minor",
                                                       "evaluation_status", "acknowledgement_required", "contra_exceptions")} if base_report else None,
        "limitations": limitations,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "not_passed_mandatory": pending,
    }
