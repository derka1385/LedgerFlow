"""Entry-level accounting checks (product/VALIDATION.md §1.1–1.2).

check(entry, txn, policy) -> list of {check_id, status, expected, observed, detail}
status: pass | fail. Independent of how the entry was produced (model, rules, human):
it re-derives what must be true from the transaction facts and the policy.
"""
from __future__ import annotations

from .admit import DEFAULT_POLICY

PURPOSE_SIDE = {"expense": "debit", "input_tax": "debit", "payment": "credit", "liability": "credit"}
SETTLEMENT_SIDE = {"liability": "debit", "payment": "credit"}


def _c(check_id: str, ok: bool, detail: str, expected=None, observed=None) -> dict:
    return {"check_id": check_id, "status": "pass" if ok else "fail",
            "expected": None if expected is None else str(expected),
            "observed": None if observed is None else str(observed), "detail": detail[:500]}


def check(entry: dict, txn: dict, policy: dict | None = None, settlement: bool = False) -> list[dict]:
    p = {**DEFAULT_POLICY, **(policy or {})}
    lines = entry["lines"]
    deb = sum(ln["amount_minor"] for ln in lines if ln["side"] == "debit")
    cre = sum(ln["amount_minor"] for ln in lines if ln["side"] == "credit")
    out = [
        _c("V-BAL-01", deb == cre, "Debits equal credits (exact öre).", deb, cre),
        _c("V-AMT-01", all(isinstance(ln["amount_minor"], int) and 0 < ln["amount_minor"] <= 10**12 for ln in lines),
           "Every amount is a positive integer of öre within bounds."),
        _c("V-SEM-06", not ({ln["account_id"] for ln in lines if ln["side"] == "debit"} &
                            {ln["account_id"] for ln in lines if ln["side"] == "credit"}),
           "No account on both sides of one entry."),
        _c("V-SEM-01", all((SETTLEMENT_SIDE if settlement else PURPOSE_SIDE).get(ln["purpose"], ln["side"]) == ln["side"]
                           for ln in lines),
           "Each line is on the side its purpose requires (purchase: cost/VAT debit, payment/liability credit; "
           "settlement: liability debit, payment credit)."),
        _c("V-EXT-01", all(ln.get("evidence_ids") for ln in lines), "Every line cites document evidence."),
    ]
    accounts = {ln["account_id"] for ln in lines}
    pay_accounts = set(p["payment_accounts"].values())
    if settlement:
        out.append(_c("V-SEM-05", accounts <= {p["payable_account"]} | pay_accounts,
                      "A settlement touches only payables and the bank (no VAT, no cost).", "2440+1940", sorted(accounts)))
        return out

    gross = txn.get("gross_minor")
    out.append(_c("V-SEM-AMT", cre == gross, "The credit total equals the document total.", gross, cre))
    deduct = txn.get("tax_treatment") == "configured_deductible"
    tax_lines = [ln for ln in lines if ln["account_id"] == p["input_tax_account"]]
    if deduct:
        out.append(_c("V-SEM-02", len(tax_lines) == 1 and tax_lines[0]["amount_minor"] == txn.get("tax_minor"),
                      "Deductible VAT is split to the input VAT account at the printed amount.",
                      txn.get("tax_minor"), [x["amount_minor"] for x in tax_lines]))
    else:
        out.append(_c("V-SEM-02", not tax_lines, "Non-deductible or tax-free purchase posts no input VAT.", 0, len(tax_lines)))

    status = txn.get("payment_status")
    credit_accounts = {ln["account_id"] for ln in lines if ln["side"] == "credit"}
    if status == "paid":
        ok = p["payable_account"] not in credit_accounts and bool(credit_accounts & pay_accounts)
        out.append(_c("V-SEM-03", ok, "Paid purchase credits a payment account, never payables (no phantom payable).",
                      sorted(pay_accounts), sorted(credit_accounts)))
    elif status == "unpaid":
        ok = credit_accounts == {p["payable_account"]}
        out.append(_c("V-SEM-03", ok, "Unpaid invoice credits payables only (no phantom bank outflow).",
                      p["payable_account"], sorted(credit_accounts)))
    else:
        out.append(_c("V-SEM-03", False, "Payment status unknown: an entry must not exist yet."))

    debit_cost = [ln for ln in lines if ln["side"] == "debit" and ln["account_id"] != p["input_tax_account"]]
    out.append(_c("V-SEM-04", all(ln["account_id"] in p["allowed_category_accounts"] for ln in debit_cost) and
                  not any(ln["account_id"].startswith("3") for ln in lines),
                  "Cost lines use allowed expense accounts; no revenue account on a purchase.",
                  "allowed list", sorted(ln["account_id"] for ln in debit_cost)))
    return out


def passed(results: list[dict]) -> bool:
    return all(r["status"] == "pass" for r in results)
