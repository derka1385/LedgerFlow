"""Frontend-facing KPI view of the benchmark (schema ledgerflow.kpis.v1).

  python3 benchmark/kpis.py      -> benchmark/results/kpis.json (served at GET /api/v1/benchmark/kpis)

Every value is copied or counted from benchmark/results/benchmark_results.json (and e2e_live.json when present);
nothing is typed by hand. Each KPI carries its source kind, its sample size and its limitation.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE / "results"


def _suite(doc, sid):
    return next((s for s in doc["suites"] if s["suite_id"] == sid and s["status"] not in ("not_run", "error")), None)


def _frac(a: int, b: int) -> dict:
    return {"value": round(100 * a / b, 1) if b else None, "numerator": a, "denominator": b, "display": f"{a}/{b}"}


def build(doc: dict, e2e: dict | None, src_sha: str) -> dict:
    k = []

    def add(kid, label, frac_or_value, unit, kind, suite_id, limitation, display=None):
        v = frac_or_value if isinstance(frac_or_value, dict) else {"value": frac_or_value, "display": display or str(frac_or_value)}
        k.append({"id": kid, "label": label, **v, "unit": unit, "source_kind": kind, "suite_id": suite_id, "limitation": limitation})

    s = _suite(doc, "accounting_correctness")
    if s:
        add("accounting_correct", "Correct entry or correct reason to stop (perfect reading)",
            _frac(s["metrics"]["correct"], s["metrics"]["cases"]), "receipts", "deterministic", s["suite_id"],
            "Ground-truth reading; isolates the rules. 21 synthetic receipts.")
    s = _suite(doc, "misread_containment")
    if s:
        m = s["metrics"]
        add("misreads_stopped", "Detectable reading errors stopped before writing",
            _frac(m["detectable_caught"], m["detectable_by_design"]), "perturbations", "deterministic", s["suite_id"],
            f"Undetectable by rules by design, left to the human approval: {', '.join(m['silent_classes'])} "
            "(wrong day in period, decimal comma lost everywhere, wrong expense account).")
    s = _suite(doc, "unauthorized_modifications")
    if s:
        m = s["metrics"]
        add("tamper_rejected", "Tampered workbooks rejected by the independent verifier",
            _frac(m["rejected_with_named_check"], m["tamper_programs"]), "programs", "sandbox", s["suite_id"],
            "16 tamper classes written by us; not an exhaustive attack catalogue.")
    s = _suite(doc, "sandbox_containment")
    if s:
        m = s["metrics"]
        add("escape_contained", "Sandbox escape probes contained", _frac(m["contained"], m["probes"]), "probes", "sandbox", s["suite_id"],
            "Docker Desktop on macOS; must be re-measured on the Vultr VM (benchmark/security_evidence.py).")
    s = _suite(doc, "formula_format_preservation")
    if s:
        rows = {r["case_id"]: r for r in s["cases"]}
        wb = "course_workbook_anonymized" if "course_workbook_anonymized/ledgerflow" in rows else "synthetic"
        lf, op = rows[f"{wb}/ledgerflow"]["kept"]["validation_ranges"], rows[f"{wb}/openpyxl"]["kept"]["validation_ranges"]
        a, b = (int(x) for x in lf.split("/"))
        add("validations_kept", "Data-validation ranges kept after a write", _frac(a, b), "ranges", "deterministic", s["suite_id"],
            f"Reference writer on the anonymized course workbook; openpyxl load+save keeps {op}.")
        k[-1]["comparison"] = {"label": "openpyxl load + save", "display": op}
    s = _suite(doc, "duplicate_detection")
    if s:
        m = s["metrics"]
        add("duplicates_caught", "Duplicate submissions held for review", _frac(m["flagged"], m["should_flag"]), "scenarios", "deterministic",
            s["suite_id"], f"{m['false_positives']} false positive(s) in {m['scenarios'] - m['should_flag']} genuine repeat purchases. "
            "DEV MOCK reference rule; Codex's backend must port it.")
    s = _suite(doc, "automatic_error_recovery")
    if s:
        m = s["metrics"]
        add("recovery_mechanism", "Faulty first programs recovered by one retry", _frac(m["recovered"], m["fault_classes"]), "fault classes",
            "scripted_model", s["suite_id"], "Mechanism only: the faulty program is scripted. Real-model retries are in the live KPIs.")
    s = _suite(doc, "structure_adaptation")
    if s:
        m = s["metrics"]
        add("layouts_handled", "Workbook layouts handled (post or refuse correctly)", _frac(m["correct"], m["variants"]), "layouts",
            "deterministic", s["suite_id"], "T-account grids only; journal-style ledgers are not supported.")

    live = doc.get("live", {})
    primary, models = None, []
    if live.get("status") == "measured":
        rec = live["recommendation"]
        prev = (live.get("previous_run") or {}).get("models", {})
        for m in live["models"]:
            mm = m["metrics"]
            if not mm.get("receipts"):
                continue
            lat = mm["latency_ms"] or {}
            e_ok, e_n = (int(x) for x in mm["end_to_end_correct"].split("/"))
            plans = mm["codegen_plans"]
            row = {"config": m["model"], "model_id": m["model_id"], "reasoning_effort": m["reasoning_effort"],
                   "booked_right": _frac(e_ok, e_n), "critical_field_accuracy_pct": mm["critical_field_accuracy_pct"],
                   "invented_critical_facts": mm["hallucinated_critical_fields"], "injection_flagged": mm["injection_detected"],
                   "code_first_try": _frac(round((mm["codegen_first_attempt_pass_pct"] or 0) * plans / 100), plans),
                   "code_after_retry": _frac(round((mm["codegen_after_repair_pass_pct"] or 0) * plans / 100), plans),
                   "read_latency_p50_s": round(lat["extraction"]["median"] / 1000, 1) if lat.get("extraction") else None,
                   "code_latency_p50_s": round(lat["codegen"]["median"] / 1000, 1) if lat.get("codegen") else None,
                   "cost_usd_per_receipt": mm["cost_usd_per_receipt"],
                   "previous_run_booked_right": (prev.get(m["model"]) or {}).get("end_to_end_correct"),
                   "recommended": m["model"] == rec["single_model"]}
            models.append(row)
            if row["recommended"]:
                primary = row
        if primary:
            add("live_booked_right", f"Receipts booked right end to end ({primary['config']}, live Vultr)", primary["booked_right"], "receipts",
                "live_vultr", "live", "22 synthetic, typeset receipts at temperature 0; previous run: "
                f"{primary['previous_run_booked_right']}. Real phone photos are not in the corpus.")
            add("live_invented", "Critical facts invented by the model", primary["invented_critical_facts"], "fields", "live_vultr", "live",
                "Over 12 critical fields x 22 receipts.")
            a, b = (int(x) for x in primary["injection_flagged"].split("/"))
            add("live_injection", "Receipts with injected instructions flagged", _frac(a, b), "receipts", "live_vultr", "live",
                "3 injection receipts (English, hidden text, Swedish).")
            add("live_code_first_try", "Generated programs verified on the first try", primary["code_first_try"], "programs", "live_vultr",
                "live", "11 plans on the synthetic workbook, real sandbox, independent verifier.")
            add("live_read_latency", "Receipt reading time, median", primary["read_latency_p50_s"], "s", "live_vultr", "live",
                "Measured from this Mac to api.vultrinference.com; excludes the account and code calls.", f"{primary['read_latency_p50_s']} s")
            add("live_cost", "Inference cost per receipt", primary["cost_usd_per_receipt"], "USD", "live_vultr", "live",
                "Tokens reported by Vultr x catalog list price; the billed amount is in the Vultr console.",
                f"{primary['cost_usd_per_receipt']:.4f} USD")
    if e2e:
        add("e2e_committed", "Final integrated run: receipts committed to Excel as expected", _frac(e2e["summary"]["as_expected"],
            e2e["summary"]["receipts"]), "receipts", "live_vultr", "e2e_live", e2e["summary"]["limitation"])

    return {"schema_version": "ledgerflow.kpis.v1", "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": {"file": "benchmark/results/benchmark_results.json", "sha256": src_sha, "benchmark_generated_at": doc["generated_at"],
                       "e2e_file": "benchmark/results/e2e_live.json" if e2e else None},
            "source_kinds": doc["source_kinds"],
            "primary_model": {"config": primary["config"], "model_id": primary["model_id"], "reasoning_effort": primary["reasoning_effort"],
                              "chosen_by": live["recommendation"]["rule"], "codegen_prompt": "v2-blank-cells-documented",
                              "budget_alternative": next((m["config"] for m in models if m["config"].startswith("mimo-v2.6-flash")), None)}
            if primary else None,
            "kpis": k, "live_models": models,
            "e2e": e2e["summary"] if e2e else None,
            "limitations": [
                "Corpus: 22 synthetic, typeset receipts (fictional companies), not phone photos; differences of one receipt are ties.",
                "Live numbers come from two runs on 27 Nov 2026 at temperature 0; run-to-run variation of one receipt was observed.",
                "Measured on a development Mac with Docker Desktop, against the DEV MOCK API that the frontend uses; Codex's production "
                "backend does not implement these flows yet and must be re-measured with the same harness.",
                "Costs are computed from tokens and catalog list prices, not from the invoice.",
                "Model-default reasoning failed often (token budget or 45 s timeout); only minimal reasoning is recommended.",
                "Sandbox numbers were measured on the infrastructure lead's tmpfs build of 27 Nov; re-run the suites after any sandbox change "
                "and on the Vultr VM (benchmark/security_evidence.py).",
            ]}


def main() -> dict:
    src = RES / "benchmark_results.json"
    raw = src.read_bytes()
    e2e_p = RES / "e2e_live.json"
    out = build(json.loads(raw), json.loads(e2e_p.read_text()) if e2e_p.exists() else None, hashlib.sha256(raw).hexdigest())
    (RES / "kpis.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    o = main()
    print(f"wrote benchmark/results/kpis.json: {len(o['kpis'])} KPIs, {len(o['live_models'])} live configurations")
