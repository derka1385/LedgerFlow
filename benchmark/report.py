"""Render BENCHMARK_RESULTS.md from benchmark_results.json. Every number comes from the JSON."""
from __future__ import annotations

import json
import sys

KIND = {"deterministic": "DETERMINISTIC", "sandbox": "REAL SANDBOX", "scripted_model": "SCRIPTED MODEL", "mock": "MOCK",
        "live_vultr": "LIVE VULTR", "not_run": "NOT RUN", "deterministic+sandbox+scripted_model": "DETERMINISTIC + SANDBOX + SCRIPTED"}


def _cell(v, key: str = "") -> str:
    if v is None:
        return "–"
    if isinstance(v, dict):
        if "median" in v:
            u = " bytes" if "bytes" in key else " ms"
            return f"median {v['median']:g}{u}, p95 {v['p95']:g}{u} (n={v['n']})"
        return ", ".join(f"{k}: {_cell(x, k)}" for k, x in v.items())
    if isinstance(v, list):
        return ", ".join(map(str, v)) or "none"
    return str(v).replace("|", "\\|").replace("\n", " ")


def _table(rows: list[dict], cols: list[tuple[str, str]]) -> list[str]:
    out = ["| " + " | ".join(h for _, h in cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        out.append("| " + " | ".join(_cell(r.get(k), k) for k, _ in cols) + " |")
    return out


def render(doc: dict) -> str:
    env = doc["environment"]
    live = doc["live"]
    L = ["# LedgerFlow agent benchmark results", "",
         f"Generated {doc['generated_at']} by `{doc['command'].strip()}` in {doc['duration_s']} s. "
         f"Machine: {env['machine']}, Python {env['python']}, Docker {env['docker_server'] or 'unavailable'}, "
         f"sandbox image `{env['sandbox_image']}` ({(env['sandbox_image_id'] or 'absent')[:19]}).",
         "Machine-readable results: `benchmark/results/benchmark_results.json` (schema `ledgerflow.benchmark.v1`). "
         "This file is generated from it; no number below was typed by hand.", "",
         "## Read this first", ""]
    if live["status"] != "measured":
        L += [f"**No live Vultr measurement exists yet.** {live['not_run_reason']} "
              "Receipt-reading accuracy, model code-generation reliability, model injection detection, latency of inference, "
              "tokens and cost are therefore **not measured** and are not estimated here.", ""]
    L += ["Every result is labelled with where it comes from:", ""]
    L += [f"- **{KIND.get(k, k)}**: {v}" for k, v in doc["source_kinds"].items()]
    L += ["", "## Headline", ""]
    L += _table(doc["headline"], [("label", "Metric"), ("value", "Value"), ("unit", "Unit"), ("source_kind", "Source")])
    if doc.get("baseline"):
        b = doc["baseline"]
        L += ["", f"## Since the baseline run ({b['generated_at']}, `{b['file']}`)", ""]
        L += _table(b["headline"], [("label", "Metric"), ("before", "Baseline"), ("after", "Now")])
        L += ["", f"Resolved findings ({len(b['resolved'])}):", ""]
        L += [f"- `{f['key']}` {f['title']}: was *{_cell(f['observed'])}*" for f in b["resolved"]] or ["- none"]
        L += ["", f"Still open: {', '.join(b['still_open']) or 'none'}. New: {', '.join(b['new']) or 'none'}."]
    L += ["", "## Findings (failed expectations)", ""]
    if doc["findings"]:
        L += _table(doc["findings"], [("severity", "Severity"), ("suite_id", "Suite"), ("case_id", "Case"), ("title", "What"),
                                      ("expected", "Expected"), ("observed", "Observed")])
    else:
        L += ["None."]
    for s in doc["suites"]:
        L += ["", f"## {s['title']}  ·  {KIND.get(s['source_kind'], s['source_kind'])}  ·  {s['status'].upper()}", ""]
        if s.get("question"):
            L += [f"*{s['question']}*", ""]
        if s["status"] == "not_run":
            L += [f"Not run: {s['not_run_reason']}"]
            continue
        L += [f"- **{k}**: {_cell(v, k)}" for k, v in s["metrics"].items()]
        if s["cases"]:
            if s["suite_id"] == "latency_deterministic":
                cols = [("title", "Stage"), ("ms", "Time")]
            else:
                cols = [("case_id", "Case"), ("title", "Scenario"), ("expected", "Expected"), ("observed", "Observed"), ("pass", "Pass")]
                if any("detail" in c for c in s["cases"]):
                    cols.append(("detail", "Detail"))
            table = _table(s["cases"], cols)
            if len(s["cases"]) > 20:  # long tables fold away; failures are always listed under Findings
                table = ["<details><summary>All " + str(len(s["cases"])) + " cases</summary>", ""] + table + ["", "</details>"]
            L += [""] + table
        if s["notes"]:
            L += [""] + [f"> {n}" for n in s["notes"]]
    L += ["", "## Live Vultr model comparison  ·  " + KIND[live["source_kind"]], ""]
    p = live["planned"]
    if live["status"] != "measured":
        L += [f"Not run: {live['not_run_reason']}", "",
              f"Ready to run on identical inputs: {p['receipts']} receipts and up to {p['codegen_plans_per_model']} code-generation plans per model, "
              "for every vision model in the live catalog (free tiers and classifiers excluded) unless `--models` narrows it."]
    else:
        cat = live["catalog"]
        L += [f"Measured {len(live['models'])} model configuration(s) in {live['duration_s']} s against `{live['base_url']}`. "
              f"{live['identical_inputs'].capitalize()}. Settings: {_cell(live['settings'])}. Code ran in the sandbox: {live['sandbox_used']}. "
              f"Prices are list prices from the public catalog retrieved {cat['retrieved_at']} (`{cat['snapshot']}`, sha256 {cat['sha256'][:12]}); "
              "cost = tokens reported by Vultr x list price. The billed amount is in the Vultr console.", ""]
        rows = []
        for m in live["models"]:
            mm = m["metrics"]
            if not mm.get("receipts"):
                rows.append({"model": m["model"], "end_to_end_correct": f"not measured ({m.get('worker_error')})"})
                continue
            lat = mm["latency_ms"] or {}
            rows.append({"model": m["model"], **mm, "read_p50": f"{lat['extraction']['median'] / 1000:.1f} s" if lat.get("extraction") else None,
                         "code_p50": f"{lat['codegen']['median'] / 1000:.1f} s" if lat.get("codegen") else None,
                         "tok": f"{sum(v['input'] for v in mm['tokens'].values())} / {sum(v['output'] for v in mm['tokens'].values())}"})
        L += _table(rows, [("model", "Model"), ("end_to_end_correct", "Booked right"), ("critical_field_accuracy_pct", "Critical fields %"),
                           ("field_accuracy_pct", "All fields %"), ("hallucinated_critical_fields", "Invented critical"),
                           ("account_accuracy_pct", "Account %"), ("injection_detected", "Injection flagged"), ("false_injection_flags", "False flags"),
                           ("inference_errors", "Errors"), ("codegen_first_attempt_pass_pct", "Code 1st try %"),
                           ("codegen_after_repair_pass_pct", "Code after retry %"), ("retry_success", "Retries that worked"),
                           ("read_p50", "Read p50"), ("code_p50", "Code p50"), ("tok", "Tokens in / out"),
                           ("cost_usd_per_receipt", "USD / receipt")])
        L += [""] + [f"> {n}" for n in live.get("notes", [])]
        sp = live.get("spend_usd_computed")
        if sp:
            L += ["", f"Computed inference spend: {sp['this_run']} USD for this run, {sp['previous_run']} USD for the previous run "
                  f"({sp['previous_run_duration_s']} s). USD / receipt = reading + account calls per receipt, plus one code-generation plan."]
        rec = live.get("recommendation") or {}
        L += ["", "### Recommendation (computed from the table above)", ""]
        measured = [m for m in live["models"] if m["metrics"].get("receipts")]
        budget = []
        if rec.get("status") == "measured" and measured:
            best = next(m for m in measured if m["model"] == rec["reader"])
            ok_n = lambda m: int(m["metrics"]["end_to_end_correct"].split("/")[0])  # noqa: E731
            near = [m for m in measured if ok_n(m) >= ok_n(best) - 1 and m["metrics"]["codegen_after_repair_pass_pct"] == 100.0
                    and m["metrics"]["cost_usd_per_receipt"] is not None]
            cheap = min(near, key=lambda m: m["metrics"]["cost_usd_per_receipt"]) if near else None
            if cheap and cheap["model"] != best["model"]:
                b, c = best["metrics"], cheap["metrics"]
                budget = [f"- **Budget alternative: `{cheap['model']}`**: {c['end_to_end_correct']} booked right vs {b['end_to_end_correct']}, "
                      f"{c['hallucinated_critical_fields']} invented critical fact(s) vs {b['hallucinated_critical_fields']}, code after retry "
                      f"{c['codegen_after_repair_pass_pct']} %, {c['cost_usd_per_receipt']} vs {b['cost_usd_per_receipt']} USD per receipt "
                      f"({round(b['cost_usd_per_receipt'] / c['cost_usd_per_receipt'], 1)}x cheaper)."]
        if rec.get("status") == "measured":
            L += [f"- **Receipt reading and accounts: `{rec['reader']}`**" + (f" (runner-up `{rec['reader_runner_up']}`, "
                  f"margin {rec['reader_margin_cases']} receipt(s){': a tie at this sample size' if rec['reader_is_tie'] else ''})" if rec.get("reader_runner_up") else ""),
                  f"- **Code generation: `{rec['coder']}`**",
                  f"- **One model for everything (what the app supports today): `{rec['single_model']}`**, configured with "
                  f"`{' '.join(f'{k}={v}' for k, v in rec['single_model_env'].items())}`. Ranking by correct outcomes "
                  f"(receipts booked right + programs that passed): {', '.join(rec['single_model_ranking'][:6])}.",
                  f"- Reader-only configuration: `{' '.join(f'{k}={v}' for k, v in rec['env'].items())}`",
                  *budget, f"- Decision rule: {rec['rule']}", f"- Note: {rec['single_model_config_note']}"]
        else:
            L += [f"No recommendation: {rec.get('status')}."]
        prev = live.get("previous_run")
        if prev:
            L += ["", f"### Code-generation prompt v1 vs v2, and repeatability (previous run: `{prev['file']}`)", "",
                  "The first live run used codegen prompt v1, which did not say that `cells()` omits blank cells; correct programs "
                  "then refused to write. v2 documents it. Reading prompts were identical in both runs, so the reading columns also "
                  "show run-to-run variation at temperature 0.", ""]
            rows = []
            for m in live["models"]:
                o = prev["models"].get(m["model"])
                if not o or not m["metrics"].get("receipts"):
                    continue
                mm = m["metrics"]
                rows.append({"model": m["model"], "e2e": f"{o['end_to_end_correct']} -> {mm['end_to_end_correct']}",
                             "c1": f"{o['codegen_first_attempt_pass_pct']} -> {mm['codegen_first_attempt_pass_pct']}",
                             "c2": f"{o['codegen_after_repair_pass_pct']} -> {mm['codegen_after_repair_pass_pct']}",
                             "inj": f"{o['injection_detected']} -> {mm['injection_detected']}"})
            L += _table(rows, [("model", "Model"), ("e2e", "Booked right (run 1 -> run 2)"), ("inj", "Injection flagged"),
                               ("c1", "Code 1st try % (v1 -> v2)"), ("c2", "Code after retry % (v1 -> v2)")])
            L += ["", "<details><summary>Run 1: all " + str(len(prev["models"])) + " configurations measured (codegen prompt v1, "
                  "model-default and minimal reasoning)</summary>", ""]
            L += _table([{"model": k, **v} for k, v in prev["models"].items()],
                        [("model", "Configuration"), ("end_to_end_correct", "Booked right"), ("critical_field_accuracy_pct", "Critical fields %"),
                         ("hallucinated_critical_fields", "Invented critical"), ("injection_detected", "Injection flagged"),
                         ("codegen_first_attempt_pass_pct", "Code 1st try %"), ("codegen_after_repair_pass_pct", "Code after retry %"),
                         ("cost_usd_per_receipt", "USD / receipt")])
            L += ["", "</details>"]
        for m in live["models"]:
            bad = [c for c in m["cases"] if not c.get("end_to_end_pass")]
            if bad:
                L += ["", f"<details><summary>{m['model']}: {len(bad)} receipt(s) not booked right</summary>", ""]
                L += _table([{"case_id": c["case_id"], "expected": c.get("expected"), "observed": c.get("observed") or c.get("error"),
                              "wrong": ", ".join(f"{k}: {v['got']!r} (printed {v['want']!r})" for k, v in (c.get("fields") or {}).items() if not v["correct"])}
                             for c in bad], [("case_id", "Receipt"), ("expected", "Expected"), ("observed", "Observed"), ("wrong", "Fields read wrong")])
                L += ["", "</details>"]
    e2e = doc.get("e2e_live")
    if e2e:
        s, f = e2e["summary"], e2e["final_workbook"]
        L += ["", f"## Final end-to-end run of the integrated application  ·  LIVE VULTR + REAL SANDBOX + REAL EXCEL", "",
              f"`python3 benchmark/e2e_live.py --excel` ({e2e['generated_at']}, {e2e['duration_s']} s, `{e2e['file']}`). Server start line: "
              f"`{e2e['server_banner']}`.", "",
              f"- **{s['as_expected']}/{s['receipts']} receipts handled as expected**; {s['committed']} committed through hash-bound approval; "
              f"all readings live: {s['all_reading_live']}; models seen: {', '.join(s['models_seen'])}.",
              f"- Final workbook: {f['versions']} versions; debits +{f['debit_increase_minor']} öre, credits +{f['credit_increase_minor']} öre "
              f"(expected +{f['expected_increase_minor']}); trial-balance gap {f['difference_minor_before_after'][0]} -> "
              f"{f['difference_minor_before_after'][1]}; data-validation ranges {f['validation_ranges_before_after'][0]} -> "
              f"{f['validation_ranges_before_after'][1]}; {f['cells_written']} cells written.",
              f"- Microsoft Excel opened a scratch copy read-only: {(f.get('excel') or {}).get('opened')}; written cells read back: "
              f"`{(f.get('excel') or {}).get('values')}` from {', '.join((f.get('excel') or {}).get('cells_read', []))}.", ""]
        L += _table(e2e["scenarios"], [("id", "Step"), ("title", "Receipt"), ("expected", "Expected"), ("observed", "Observed"),
                                       ("entry", "Entry"), ("verifier", "Verifier"), ("runtime", "Runtime"), ("seconds_to_ready", "Seconds")])
        L += ["", f"> {s['limitation']}"]
    fsu = doc.get("final_suite")
    if fsu:
        L += ["", "## Release suite on the demo package  ·  LIVE VULTR + REAL SANDBOX", "",
              f"`python3 demo/final_suite.py --spawn` ({fsu['generated_at']}, {fsu['duration_s']} s, `{fsu['file']}`): "
              f"**{fsu['passed']}/{fsu['total']} passed, {fsu['failed']} failed, {fsu['not_run']} not run.**", ""]
        L += _table([{**x, "result": "PASS" if x["pass"] else ("not run" if x["pass"] is None else "FAIL")} for x in fsu["steps"]],
                    [("step", "Step"), ("title", "Check"), ("result", "Result")])
    L += ["", "### How to run live (the key never enters the chat, a file or a log)", "",
          "Store the key once in the macOS Keychain; `security` prompts for it without echo:", "",
          "```bash", "security add-generic-password -a \"$USER\" -s ledgerflow-vultr-inference -w", "```", "",
          "Smoke test (2 receipts, 1 code plan, 1 model), then the full comparison:", "",
          "```bash", "python3 benchmark/bench.py --live-only --live --models glm-5.3-flash --receipts R01,R13 --codegen-cases 1 --out benchmark/results/live_smoke.json --md benchmark/results/live_smoke.md", "```", "",
          "```bash", "python3 benchmark/bench.py --live-only --live", "```", "",
          "Alternatives, in this order of precedence: `VULTR_INFERENCE_API_KEY` in the environment, then the git-ignored `.env` at the repo root (chmod 600), then the Keychain. `--live-only` keeps the local suites from the last full run (`benchmark/results/benchmark_results.json`)."]
    L += ["", "## How to reproduce", "", "```bash", "python3 benchmark/corpus.py", "```", "", "```bash", "python3 benchmark/bench.py", "```", "",
          "Needs Docker and `python:3.12-slim` for the sandbox suites (`--no-sandbox` runs the rest).", ""]
    return "\n".join(L)


if __name__ == "__main__":
    print(render(json.load(open(sys.argv[1]))))
