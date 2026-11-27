"""Deterministic admission: TransactionV1 + policy -> EntryV1, or named review reasons.

Implements product/ACCOUNTING_RULES.md (decision tree §4, templates §5, VAT
deductibility §3) on Codex's contracts (docs/DATA_SCHEMAS.md). The model never
writes debits/credits; this module does. Integer minor units only.

Review codes follow docs/API_CONTRACT.md where one exists
(PAYMENT_CONTEXT_REQUIRED, TAX_REVIEW_REQUIRED, ...). Codes this module adds are
listed in REVIEW_CODES and in FRONTEND_HANDOFF.md.
"""
from __future__ import annotations

from datetime import date

REVIEW_CODES = {
    "FIELD_REVIEW_REQUIRED": "A required fact is unknown or unreadable on the document.",
    "PAYMENT_CONTEXT_REQUIRED": "How (or whether) this was paid is not evidenced.",
    "TAX_REVIEW_REQUIRED": "VAT amount, rate or deductibility needs a human decision.",
    "ACCOUNT_REVIEW_REQUIRED": "No expense account was chosen, or the chosen one is not allowed.",
    "AMOUNTS_INCONSISTENT": "Printed net + VAT does not equal the total.",
    "CURRENCY_UNSUPPORTED": "Only SEK is supported in this version.",
    "PERIOD_CLOSED": "The document date is outside the open accounting period.",
    "EVIDENCE_MISSING": "A posted amount has no document evidence.",
    "UNSUPPORTED_KIND": "This document type is not supported in this version.",
}

DEFAULT_POLICY = {
    "policy_version": "policy_nordvik_v1",
    "currency": "SEK",
    "vat_registered": True,
    "payment_accounts": {"company_bank": "1940", "company_cash": "1910"},
    "payable_account": "2440",
    "input_tax_account": "2640",
    "reimbursement_liability_account": None,  # not in the SSE chart -> employee_personal is held
    "allowed_category_accounts": ["4010", "5010", "5170", "5420", "6110", "6210", "6540", "6570", "6810"],
    "valid_rates_bp": [2500, 1200, 600],
    # Skatteverket: food 6 % only from 2026-04-01 (was 12 %). Rate validity by date is
    # enforced for the food scope only when a category declares it (none in this chart).
    "simplified_invoice_limit_minor": 400_000,  # 4,000 SEK incl. VAT
    "require_seller_id_for_deduction": True,
    "open_from": "2026-01-01",
    "open_to": "2026-12-31",
    "tax_tolerance_minor_per_line": 1,
}


def _review(code: str, field: str | None, detail: str) -> dict:
    return {"code": code, "field": field, "message": REVIEW_CODES.get(code, code), "detail": detail}


def _evidence_ids(txn: dict, *fields: str) -> list[str]:
    ids = [e["evidence_id"] for e in txn.get("evidence", []) if e.get("field") in fields and e.get("status") != "unreadable"]
    return ids[:10]


def admit(txn: dict, policy: dict | None = None, today: str | None = None) -> dict:
    """Return {"admitted": bool, "entry": EntryV1 | None, "review": [..], "advisories": [..]}."""
    p = {**DEFAULT_POLICY, **(policy or {})}
    review: list[dict] = []
    advisories: list[str] = []

    for f in txn.get("unresolved_fields", []):
        code = ("PAYMENT_CONTEXT_REQUIRED" if f.startswith("payment") else
                "TAX_REVIEW_REQUIRED" if f.startswith("tax") else
                "ACCOUNT_REVIEW_REQUIRED" if f == "category_account_id" else "FIELD_REVIEW_REQUIRED")
        review.append(_review(code, f, f"{f.replace('_minor', '').replace('_', ' ').capitalize()} is not shown on the document."))

    kind = txn.get("kind")
    if kind not in ("purchase_receipt", "supplier_invoice"):
        review.append(_review("UNSUPPORTED_KIND", "kind", f"kind={kind!r}"))

    if txn.get("currency") != p["currency"]:
        review.append(_review("CURRENCY_UNSUPPORTED", "currency", f"currency={txn.get('currency')!r}"))

    d = txn.get("document_date")
    if d is None:
        review.append(_review("FIELD_REVIEW_REQUIRED", "document_date", "No document date."))
    elif not _valid_iso(d):
        review.append(_review("FIELD_REVIEW_REQUIRED", "document_date", f"Not an ISO date: {d!r}"))
    else:
        if not (p["open_from"] <= d <= p["open_to"]):
            review.append(_review("PERIOD_CLOSED", "document_date", f"{d} not in {p['open_from']}..{p['open_to']}"))
        if today and d > today:
            review.append(_review("FIELD_REVIEW_REQUIRED", "document_date", f"{d} is in the future"))

    gross, net, tax = txn.get("gross_minor"), txn.get("net_minor"), txn.get("tax_minor")
    if gross is None or gross <= 0:
        review.append(_review("FIELD_REVIEW_REQUIRED", "gross_minor", "No positive total."))

    # --- VAT ---------------------------------------------------------------
    treatment = txn.get("tax_treatment", "unknown")
    lines_tax = txn.get("tax_lines", [])
    deduct = False
    if treatment == "unknown":
        review.append(_review("TAX_REVIEW_REQUIRED", "tax_treatment", "VAT treatment not decided."))
    elif treatment == "configured_deductible":
        deduct = True
        if not p["vat_registered"]:
            review.append(_review("TAX_REVIEW_REQUIRED", "tax_treatment", "Company is not VAT-registered."))
        if tax is None or net is None or tax <= 0:
            review.append(_review("TAX_REVIEW_REQUIRED", "tax_minor", "Deductible VAT needs printed net and VAT amounts."))
        if len(lines_tax) != 1:
            review.append(_review("TAX_REVIEW_REQUIRED", "tax_lines", f"{len(lines_tax)} VAT lines: mixed or missing rates go to review in P0."))
        for tl in lines_tax:
            rate = tl.get("rate_basis_points")
            if rate not in p["valid_rates_bp"]:
                review.append(_review("TAX_REVIEW_REQUIRED", "tax_lines", f"Rate {rate} bp is not a valid Swedish rate."))
            elif tl.get("base_minor") is not None and tl.get("tax_minor") is not None:
                expected = (tl["base_minor"] * rate + 5000) // 10000
                if abs(expected - tl["tax_minor"]) > p["tax_tolerance_minor_per_line"]:
                    review.append(_review("TAX_REVIEW_REQUIRED", "tax_lines",
                                          f"VAT {tl['tax_minor']} öre is not {rate / 100:g} % of {tl['base_minor']} öre (expected {expected})."))
        if p["require_seller_id_for_deduction"] and not txn.get("supplier_org_no"):
            review.append(_review("TAX_REVIEW_REQUIRED", "supplier_org_no", "Seller VAT/org number not on the document; deduction at risk."))
        if gross is not None and gross > p["simplified_invoice_limit_minor"] and not txn.get("supplier_reference"):
            review.append(_review("TAX_REVIEW_REQUIRED", "supplier_reference",
                                  "Above 4,000 SEK a full invoice (with invoice number) is required to deduct VAT."))
        if gross is not None and gross > p["simplified_invoice_limit_minor"]:
            # Kvittion spec slide 9-10: above SEK 4,000 a full invoice (buyer name and address, seller VAT no.) is needed for the
            # deduction. Buyer details are not extracted, so the approver is told to check them (non-blocking).
            advisories.append("Above SEK 4,000 incl. VAT: deduct VAT only if the document is a full invoice showing the buyer's name "
                              "and address and the seller's VAT number. LedgerFlow does not check buyer details; verify before approving.")
    elif treatment == "tax_free":
        if tax not in (None, 0) or lines_tax:
            review.append(_review("TAX_REVIEW_REQUIRED", "tax_minor", "Marked tax-free but VAT is printed."))
    elif treatment == "configured_nondeductible":
        advisories.append("VAT is booked as part of the cost (non-deductible by policy).")

    if None not in (gross, net, tax) and net + tax != gross:
        review.append(_review("AMOUNTS_INCONSISTENT", "gross_minor", f"net {net} + VAT {tax} = {net + tax} ≠ total {gross} (öre)."))
    if lines_tax and tax is not None and all(tl.get("tax_minor") is not None for tl in lines_tax):
        if sum(tl["tax_minor"] for tl in lines_tax) != tax:
            review.append(_review("AMOUNTS_INCONSISTENT", "tax_lines", "VAT lines do not add up to the VAT total."))

    # --- account -----------------------------------------------------------
    category = txn.get("category_account_id")
    if category is None:
        review.append(_review("ACCOUNT_REVIEW_REQUIRED", "category_account_id", "No expense account chosen."))
    elif category not in p["allowed_category_accounts"]:
        review.append(_review("ACCOUNT_REVIEW_REQUIRED", "category_account_id", f"Account {category} is not allowed for purchases by policy."))

    # --- payment (never assumed) -------------------------------------------
    status, source = txn.get("payment_status", "unknown"), txn.get("payment_source", "unknown")
    credit_account, credit_purpose = None, None
    if status == "unknown":
        review.append(_review("PAYMENT_CONTEXT_REQUIRED", "payment_status", "Payment status not evidenced."))
    elif status == "unpaid":
        if kind == "purchase_receipt":
            review.append(_review("PAYMENT_CONTEXT_REQUIRED", "payment_status", "A receipt marked unpaid is contradictory."))
        credit_account, credit_purpose = p["payable_account"], "liability"
    elif status == "paid":
        if source in p["payment_accounts"]:
            credit_account, credit_purpose = p["payment_accounts"][source], "payment"
        elif source == "employee_personal" and p["reimbursement_liability_account"]:
            credit_account, credit_purpose = p["reimbursement_liability_account"], "liability"
        else:
            review.append(_review("PAYMENT_CONTEXT_REQUIRED", "payment_source",
                                  "Paid privately or from an unknown account; no reimbursement account is configured."))
        given = txn.get("payment_account_id")
        if given and credit_account and given != credit_account:
            review.append(_review("PAYMENT_CONTEXT_REQUIRED", "payment_account_id",
                                  f"Payment account {given} conflicts with policy account {credit_account} for {source}."))

    ev_amount = _evidence_ids(txn, "gross_minor", "net_minor", "tax_minor", "tax_lines")
    if gross is not None and not ev_amount:
        review.append(_review("EVIDENCE_MISSING", "gross_minor", "No evidence id supports the amounts."))

    if review:
        return {"admitted": False, "entry": None, "review": _dedupe(review), "advisories": advisories}

    ev_cat = _evidence_ids(txn, "category_account_id", "merchant_name") or ev_amount[:1]
    ev_pay = _evidence_ids(txn, "payment_status", "payment_source", "payment_account_id") or ev_amount[:1]
    ev_tax = _evidence_ids(txn, "tax_minor", "tax_lines", "tax_treatment") or ev_amount[:1]
    cost = net if deduct else gross
    lines = [{"line_id": "line_expense", "account_id": category, "side": "debit", "amount_minor": cost,
              "purpose": "expense", "evidence_ids": sorted(set(ev_amount[:5] + ev_cat[:5]))[:10]}]
    if deduct:
        lines.append({"line_id": "line_tax", "account_id": p["input_tax_account"], "side": "debit", "amount_minor": tax,
                      "purpose": "input_tax", "evidence_ids": sorted(set(ev_tax))[:10]})
    lines.append({"line_id": "line_credit", "account_id": credit_account, "side": "credit", "amount_minor": gross,
                  "purpose": credit_purpose, "evidence_ids": sorted(set(ev_amount[:5] + ev_pay[:5]))[:10]})

    def sek(m: int) -> str:
        return f"{m // 100:,}.{m % 100:02d}".replace(",", " ")

    how = {"payment": f"paid from {credit_account}", "liability": f"unpaid, booked to payables {credit_account}"}[credit_purpose]
    vat_txt = f" + deductible VAT SEK {sek(tax)}" if deduct else ""
    entry = {
        "entry_id": f"entry_{txn['transaction_id']}_{txn['revision']}",
        "transaction_id": txn["transaction_id"],
        "transaction_revision": txn["revision"],
        "accounting_date": d,
        "currency": "SEK",
        "policy_version": p["policy_version"],
        "lines": lines,
        "explanation": f"{txn.get('merchant_name') or 'Supplier'}: SEK {sek(cost)} to {category}{vat_txt}; total SEK {sek(gross)} {how}.",
        "source_evidence_ids": sorted({e for ln in lines for e in ln["evidence_ids"]})[:20],
    }
    return {"admitted": True, "entry": entry, "review": [], "advisories": advisories}


def admit_settlement(payment: dict, open_items: list[dict], policy: dict | None = None) -> dict:
    """Extension (not yet in Codex's TransactionV1 kinds): settle one open payable.

    payment: {transaction_id, revision, date, amount_minor, reference, supplier_name, evidence_ids}
    open_items: [{open_item_id, supplier_name, reference, gross_minor, status}]
    """
    p = {**DEFAULT_POLICY, **(policy or {})}
    opens = [o for o in open_items if o["status"] == "open"]
    ref = (payment.get("reference") or "").strip()
    cands = [o for o in opens if ref and ref in (o.get("reference") or "", o.get("ocr") or "")]
    if not cands:
        name = (payment.get("supplier_name") or "").casefold().strip()
        cands = [o for o in opens if o["supplier_name"].casefold().strip() == name and o["gross_minor"] == payment["amount_minor"]]
    if len(cands) != 1:
        return {"admitted": False, "entry": None, "matched": None,
                "review": [_review("PAYMENT_CONTEXT_REQUIRED", "reference", f"{len(cands)} open invoices match; exactly one is required.")]}
    item = cands[0]
    if item["gross_minor"] != payment["amount_minor"]:
        return {"admitted": False, "entry": None, "matched": item["open_item_id"],
                "review": [_review("PAYMENT_CONTEXT_REQUIRED", "amount_minor", "Partial or over-payment: human decides.")]}
    ev = payment.get("evidence_ids") or []
    if not ev:
        return {"admitted": False, "entry": None, "matched": item["open_item_id"],
                "review": [_review("EVIDENCE_MISSING", "amount_minor", "No payment evidence.")]}
    amt = payment["amount_minor"]
    entry = {"entry_id": f"entry_{payment['transaction_id']}_{payment['revision']}", "transaction_id": payment["transaction_id"],
             "transaction_revision": payment["revision"], "accounting_date": payment["date"], "currency": "SEK",
             "policy_version": p["policy_version"],
             "lines": [{"line_id": "line_payable", "account_id": p["payable_account"], "side": "debit", "amount_minor": amt,
                        "purpose": "liability", "evidence_ids": ev[:10]},
                       {"line_id": "line_payment", "account_id": p["payment_accounts"]["company_bank"], "side": "credit",
                        "amount_minor": amt, "purpose": "payment", "evidence_ids": ev[:10]}],
             "explanation": f"Payment of open invoice {item.get('reference')} to {item['supplier_name']}.",
             "source_evidence_ids": ev[:20]}
    return {"admitted": True, "entry": entry, "matched": item["open_item_id"], "review": []}


def _dedupe(items: list[dict]) -> list[dict]:
    seen, out = set(), []
    for it in items:
        k = (it["code"], it["field"], it["detail"])
        if k not in seen:
            seen.add(k)
            out.append(it)
    return out


def _valid_iso(d: str) -> bool:
    try:
        date.fromisoformat(d)
        return True
    except ValueError:
        return False
