"""Checks for the benchmark harness itself (no Docker, no network). Run: python3 -m pytest benchmark -q"""
from __future__ import annotations

import errno
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench  # noqa: E402


def test_scorer_rewards_truth_and_flags_errors():
    truth = bench.BY_ID["R01"]["truth"]
    perfect = bench.score_extraction(bench.oracle_extraction(truth), truth)
    assert all(f["correct"] for f in perfect.values())
    wrong = bench.oracle_extraction(truth)
    wrong["gross"]["value"] = "899,00 "  # formatting differences are not errors
    wrong["vat"]["value"] = "180.80"
    wrong["due_date"] = {"status": "known", "value": "2026-12-01", "quote": "x"}  # not printed: hallucination
    s = bench.score_extraction(wrong, truth)
    assert s["gross"]["correct"] and not s["vat"]["correct"] and s["due_date"]["hallucinated"]


def test_every_corpus_case_has_a_reachable_expectation():
    acc = bench.s_accounting()
    assert len(acc["cases"]) == len([c for c in bench.CASES if not c.get("same_as")])
    for c in bench.CASES:
        assert set(c["truth"]) == set(bench.FIELDS), c["id"]


def test_live_path_plumbing_against_a_scripted_server():
    """Not a model measurement: proves the live harness wiring, scoring, token and cost accounting."""
    srv, url = bench.start_fake()
    r01 = bench.BY_ID["R01"]

    def script(body):
        system = body["messages"][0]["content"]
        if "receipts" in system:
            return json.dumps(bench.oracle_extraction(r01["truth"]))
        if "classify" in system:
            return json.dumps({"proposed_account": "6110", "alternatives": [], "rationale": "office supplies"})
        return "```python\n" + bench.programs.MOCK_GENERATED_PROGRAM + "```"

    bench.Fake.script, bench.Fake.usage = script, {"prompt_tokens": 10, "completion_tokens": 5}
    saved = (bench.vsi.BASE, bench.vsi.MODEL, os.environ.get("VULTR_INFERENCE_API_KEY"))
    bench.vsi.BASE = url
    os.environ["VULTR_INFERENCE_API_KEY"] = "test"
    try:
        prices = {"glm-5.3-flash": {"usd_per_1m_input": 0.10, "usd_per_1m_output": 0.35}}
        res = bench.live_model("glm-5.3-flash", codegen_cases=1, with_sandbox=False, prices=prices)
    finally:
        bench.vsi.BASE, bench.vsi.MODEL = saved[0], saved[1]
        os.environ.pop("VULTR_INFERENCE_API_KEY", None) if saved[2] is None else os.environ.update(VULTR_INFERENCE_API_KEY=saved[2])
        srv.shutdown()
        bench.Fake.usage = {"prompt_tokens": 0, "completion_tokens": 0}
    rows = {r["case_id"]: r for r in res["cases"]}
    assert all(f["correct"] for f in rows["R01"]["fields"].values()) and rows["R01"]["end_to_end_pass"]
    assert not rows["R02"]["end_to_end_pass"]  # the script always answers R01, so other receipts must score as wrong
    assert res["codegen"][0]["attempts"] == [{"result": "not_executed (no sandbox)"}]
    m = res["metrics"]
    t = m["tokens"]["extraction"]
    assert t["input"] > 0 and m["cost_usd"]["extraction"] == round((t["input"] * 0.10 + t["output"] * 0.35) / 1e6, 6)
    rec = bench.recommend([res])
    assert rec["reader"] == "glm-5.3-flash" and rec["env"] == {"LEDGERFLOW_VSI_MODEL": "glm-5.3-flash"}


def test_deterministic_suites_have_no_findings():
    """Regression guard for what the benchmark found (R02 unpaid invoice, D02-D06 duplicates)."""
    acc = bench.s_accounting()
    for s in (acc, bench.s_misreads(acc), bench.s_duplicates(), bench.s_structure()):
        assert [c["case_id"] for c in s["cases"] if c.get("pass") is False] == [], s["suite_id"]


@pytest.mark.parametrize("limit,error,contained", [
    (126, errno.EAGAIN, True),
    (0, errno.EAGAIN, False),
    (128, errno.EAGAIN, False),
    (126, errno.EACCES, False),
    (400, None, False),
])
def test_fork_probe_requires_pid_denial_and_reaps_children(monkeypatch, capsys, limit, error, contained):
    """Exercise the real probe with fake fork syscalls; never fork on the test host."""
    created, reaped = [], []

    def fork():
        if len(created) == limit and error is not None:
            raise OSError(error, "simulated fork denial")
        pid = len(created) + 100
        created.append(pid)
        return pid

    def waitpid(pid, options):
        assert options == 0
        reaped.append(pid)
        return pid, 0

    code = next(code for pid, _, code, _ in bench.faults.PROBES if pid == "P10")
    with monkeypatch.context() as mocked:
        mocked.setitem(sys.modules, "os", SimpleNamespace(fork=fork, waitpid=waitpid))
        exec(compile(code, "P10", "exec"), {})
    result = json.loads(capsys.readouterr().out.removeprefix("RESULT "))
    assert result["contained"] is contained
    assert reaped == created
