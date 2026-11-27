"""T-account workbook engine (layout `t_accounts`, SSE style).

Pure functions over a read-only Workbook:
  detect_mapping()  -> account blocks + writable rows, derived from the
                       workbook's own list validations (product spec
                       WORKBOOK_ANALYSIS F5)
  parse_lines()     -> every posted line, opening balances included
  trial_balance()   -> exact integer minor units per account
  contra_exceptions()-> lines without a reciprocal mirror (finds the G48 class)
  allocate()        -> CellOperationV1 + PostingAllocationV1 for an EntryV1

Money is integer minor units (SEK, exponent 2) everywhere.
"""
from __future__ import annotations

import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation

from .ooxml import BLANK, Cell, Workbook, WorkbookError, col_to_num, num_to_col, split_cell

HEADER_RE = re.compile(r"^\s*(\d{4})\s+(.+?)\s*$")
REF_RE = re.compile(r"^\[(\d{4}|OB)\]$")
CHART_CODE_RE = re.compile(r"^\[(\d{4})\]$")
MAX_MINOR = 10**12


def to_minor(value: str | None) -> int:
    """Exact major-unit decimal string -> integer öre. Refuses sub-öre values."""
    if value is None:
        raise WorkbookError("AMOUNT_MISSING", "Amount cell has no value")
    try:
        d = Decimal(str(value)) * 100
    except InvalidOperation as exc:
        raise WorkbookError("AMOUNT_INVALID", f"Not a number: {value!r}") from exc
    if d != d.to_integral_value():
        raise WorkbookError("AMOUNT_PRECISION", f"Amount has more than 2 decimals: {value}")
    return int(d)


def minor_to_excel(minor: int) -> str:
    """Integer öre -> exact decimal string written to <v>."""
    if not 0 < minor <= MAX_MINOR:
        raise WorkbookError("AMOUNT_RANGE", f"Amount out of range: {minor}")
    major, ore = divmod(minor, 100)
    return str(major) if ore == 0 else f"{major}.{ore:02d}"


def role_for(code: str) -> str:
    if code.startswith("20"):
        return "equity"
    if code.startswith("26"):
        return "tax"
    return {"1": "asset", "2": "liability", "3": "income", "4": "expense", "5": "expense",
            "6": "expense", "7": "expense"}.get(code[0], "income" if code.startswith("83") else "expense")


def _cell_text(cell: Cell | None) -> str | None:
    if cell is None or cell.type == "blank":
        return None
    return str(cell.value).strip() if cell.value is not None else None


def find_chart(wb: Workbook) -> tuple[str, dict[str, str]]:
    """Sheet holding '[NNNN]' codes in column A with names in column B."""
    for name in wb.sheets:
        cells = wb.cells(name)
        chart = {}
        for ref, cell in cells.items():
            col, row = split_cell(ref)
            m = CHART_CODE_RE.match(_cell_text(cell) or "")
            if col == "A" and m:
                chart[m.group(1)] = (_cell_text(cells.get(f"B{row}")) or "").strip()
        if len(chart) >= 5:
            return name, chart
    raise WorkbookError("UNSUPPORTED_WORKBOOK", "No chart-of-accounts sheet ([NNNN] codes in column A) found")


def detect_mapping(wb: Workbook) -> dict:
    """Derive the t_accounts mapping. Raises WorkbookError if the layout is not recognised."""
    chart_sheet, chart = find_chart(wb)
    best = None
    for name in wb.sheets:
        if name == chart_sheet:
            continue
        cells = wb.cells(name)
        dv = wb.list_validation_cells(name)
        headers = []
        for ref, cell in cells.items():
            m = HEADER_RE.match(_cell_text(cell) or "")
            if m and m.group(1) in chart:
                headers.append((ref, m.group(1), m.group(2)))
        if len(headers) >= 4 and dv and (best is None or len(headers) > len(best[1])):
            best = (name, headers, cells, dv)
    if best is None:
        raise WorkbookError("UNSUPPORTED_WORKBOOK", "No T-account sheet (4-column account blocks with list validations) found")
    sheet, headers, cells, dv = best
    merged = {}
    for rng in wb.merged_ranges(sheet):
        a, _, b = rng.partition(":")
        merged[a] = split_cell(b or a)[1]

    accounts = {}
    for ref, code, name in headers:
        col, row = split_cell(ref)
        body = merged.get(ref, row) + 1
        c = col_to_num(col)
        sides = {}
        for side, ref_c in (("debit", c), ("credit", c + 2)):
            rc, ac = num_to_col(ref_c), num_to_col(ref_c + 1)
            rows = []
            r = body if f"{rc}{body}" in dv else body + 1
            while f"{rc}{r}" in dv and r < body + 60:
                rows.append(r)
                r += 1
            ob_cell = f"{rc}{body}" if _cell_text(cells.get(f"{rc}{body}")) == "[OB]" else None
            sides[side] = {"reference_column": rc, "amount_column": ac, "writable_rows": rows,
                           "first_row": rows[0] if rows else None, "last_row": rows[-1] if rows else None,
                           "opening_balance_cell": ob_cell, "reference_format": "bracketed_account_id"}
        accounts[code] = {"account_id": code, "name": name, "chart_name": chart.get(code), "role": role_for(code),
                          "sheet": sheet, "header_cell": ref, "body_row": body, **sides}
    missing = sorted(set(chart) - set(accounts))
    formulas = [{"sheet": sheet, "cell": r, "formula": c.formula, "cached_value": c.value}
                for r, c in cells.items() if c.type == "formula"]
    return {"layout": "t_accounts", "sheet": sheet, "chart_sheet": chart_sheet, "accounts": accounts,
            "chart_accounts_without_block": missing, "formulas": formulas,
            "slot_count": sum(len(a[s]["writable_rows"]) for a in accounts.values() for s in ("debit", "credit"))}


def parse_lines(wb: Workbook, mapping: dict) -> tuple[list[dict], list[dict]]:
    """Every (reference, amount) pair on every side, OB rows included. Returns (lines, anomalies)."""
    cells = wb.cells(mapping["sheet"])
    lines, anomalies = [], []
    for code, acc in mapping["accounts"].items():
        for side in ("debit", "credit"):
            s = acc[side]
            rows = sorted(set(s["writable_rows"]) | {acc["body_row"]})
            for r in rows:
                rc, ac = f"{s['reference_column']}{r}", f"{s['amount_column']}{r}"
                ref, amt = _cell_text(cells.get(rc)), cells.get(ac)
                amt_val = None if amt is None else amt.value
                if ref is None and amt_val is None:
                    continue
                m = REF_RE.match(ref or "")
                if not m or amt_val is None:
                    anomalies.append({"account_id": code, "side": side, "reference_cell": rc, "amount_cell": ac,
                                      "reference": ref, "amount": amt_val, "reason": "incomplete_or_invalid_line"})
                    continue
                lines.append({"account_id": code, "side": side, "contra": m.group(1), "amount_minor": to_minor(amt_val),
                              "reference_cell": rc, "amount_cell": ac, "row": r,
                              "from_formula": amt.type == "formula"})
    return lines, anomalies


def trial_balance(lines: list[dict]) -> dict:
    per = defaultdict(lambda: {"debit_minor": 0, "credit_minor": 0})
    for ln in lines:
        per[ln["account_id"]][f"{ln['side']}_minor"] += ln["amount_minor"]
    debits = sum(v["debit_minor"] for v in per.values())
    credits = sum(v["credit_minor"] for v in per.values())
    return {"accounts": dict(sorted(per.items())), "debits_minor": debits, "credits_minor": credits,
            "difference_minor": debits - credits}


def contra_exceptions(lines: list[dict]) -> list[dict]:
    """Lines whose reciprocal (contra account, opposite side, referencing back, same amount) is missing."""
    pool = [ln for ln in lines if ln["contra"] != "OB"]
    used: set[int] = set()
    out = []
    for i, a in enumerate(pool):
        if i in used:
            continue
        for j, b in enumerate(pool):
            if j != i and j not in used and b["account_id"] == a["contra"] and b["contra"] == a["account_id"] \
                    and b["side"] != a["side"] and b["amount_minor"] == a["amount_minor"]:
                used.update((i, j))
                break
        else:
            out.append(a)
    return out


def baseline(wb: Workbook, mapping: dict) -> dict:
    lines, anomalies = parse_lines(wb, mapping)
    tb = trial_balance(lines)
    ob = [ln for ln in lines if ln["contra"] == "OB"]
    ob_d = sum(x["amount_minor"] for x in ob if x["side"] == "debit")
    ob_c = sum(x["amount_minor"] for x in ob if x["side"] == "credit")
    exc = contra_exceptions(lines)
    return {"debits_minor": tb["debits_minor"], "credits_minor": tb["credits_minor"],
            "difference_minor": tb["difference_minor"], "accounts": tb["accounts"],
            "opening_debits_minor": ob_d, "opening_credits_minor": ob_c,
            "contra_exceptions": [{k: e[k] for k in ("account_id", "side", "contra", "amount_minor", "amount_cell")} for e in exc],
            "anomalies": anomalies, "line_count": len(lines),
            "used_slots": len([ln for ln in lines if ln["contra"] != "OB"]),
            "evaluation_status": "complete_supported" if not anomalies else "incomplete",
            "acknowledgement_required": tb["difference_minor"] != 0 or bool(exc) or bool(anomalies)}


def _free_rows(cells: dict[str, Cell], acc: dict, side: str, taken: set[str]) -> list[int]:
    s = acc[side]
    used = [r for r in s["writable_rows"]
            if _cell_text(cells.get(f"{s['reference_column']}{r}")) is not None or
            (cells.get(f"{s['amount_column']}{r}") or BLANK).type != "blank"]
    start = max(used) + 1 if used else (s["first_row"] or 0)
    return [r for r in s["writable_rows"] if r >= start and f"{s['reference_column']}{r}" not in taken]


def legs_for(entry_lines: list[dict]) -> list[tuple[dict, dict, int]]:
    """Split a one-to-many entry into pairwise (debit line, credit line, amount) legs."""
    debits = [ln for ln in entry_lines if ln["side"] == "debit"]
    credits = [ln for ln in entry_lines if ln["side"] == "credit"]
    if len(credits) == 1:
        return [(d, credits[0], d["amount_minor"]) for d in debits]
    if len(debits) == 1:
        return [(debits[0], c, c["amount_minor"]) for c in credits]
    raise WorkbookError("ALLOCATION_AMBIGUOUS", "Many-to-many entries need an explicit allocation matrix (P0 refuses)")


def allocate(wb: Workbook, mapping: dict, entry: dict) -> dict:
    """Deterministic slot reservation -> {operations, posting_allocations}. Raises NO_SAFE_SLOTS."""
    sheet = mapping["sheet"]
    cells = wb.cells(sheet)
    styles = wb.style_ids(sheet)
    taken: set[str] = set()
    ops, allocs = [], []
    for n, (d, c, amount) in enumerate(legs_for(entry["lines"]), start=1):
        alloc_id = f"alloc_{n}"
        pair_cells = {}
        for line, side, contra_code, role in ((d, "debit", c["account_id"], "debit"), (c, "credit", d["account_id"], "credit")):
            acc = mapping["accounts"].get(line["account_id"])
            if acc is None:
                raise WorkbookError("ACCOUNT_NOT_MAPPED", f"Account {line['account_id']} has no T-account block")
            free = _free_rows(cells, acc, side, taken)
            if not free:
                raise WorkbookError("NO_SAFE_SLOTS", f"Account {line['account_id']} has no free {side} row")
            r = free[0]
            s = acc[side]
            rc, ac = f"{s['reference_column']}{r}", f"{s['amount_column']}{r}"
            taken.add(rc)
            for cell, after, op_role in ((rc, {"type": "text", "value": f"[{contra_code}]"}, f"{role}_reference"),
                                         (ac, {"type": "number", "value": minor_to_excel(amount)}, f"{role}_amount")):
                before = cells.get(cell, Cell("blank", None, None, styles.get(cell)))
                if before.type != "blank":
                    raise WorkbookError("NO_SAFE_SLOTS", f"Target {cell} is not blank")
                ops.append({"sheet": sheet, "cell": cell, "before": before.as_dict(), "after": after,
                            "line_id": line["line_id"], "allocation_id": alloc_id, "role": op_role})
            pair_cells[side] = [{"sheet": sheet, "cell": rc}, {"sheet": sheet, "cell": ac}]
        allocs.append({"allocation_id": alloc_id, "debit_line_id": d["line_id"], "credit_line_id": c["line_id"],
                       "amount_minor": amount, "debit_cells": pair_cells["debit"], "credit_cells": pair_cells["credit"]})
    return {"operations": ops, "posting_allocations": allocs}
