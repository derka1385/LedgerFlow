"""The shipped prompts and primary model are exactly what config/inference.json publishes for Codex's backend."""
import hashlib
import json
from pathlib import Path

import vsi

CFG = json.loads((Path(__file__).resolve().parents[2] / "config" / "inference.json").read_text())
h = lambda t: hashlib.sha256(t.encode()).hexdigest()  # noqa: E731


def test_prompts_match_the_published_hashes():
    p = CFG["prompts"]
    assert h(vsi.EXTRACTION_SYSTEM) == p["extraction_system_sha256"]
    assert h(vsi.ACCOUNT_SYSTEM) == p["account_system_sha256"]
    assert h(vsi.CODEGEN_SYSTEM) == p["codegen_system_sha256"]
    assert vsi.CODEGEN_PROMPT_VERSION == p["codegen_version"] == "v2-blank-cells-documented"
    assert "ABSENT from the dict" in vsi.CODEGEN_SYSTEM


def test_primary_model_is_the_measured_choice():
    assert (CFG["model"], CFG["reasoning_effort"]) == ("qwen3.8-27b", "minimal")
    assert "KEY" not in json.dumps({k: v for k, v in CFG.items() if k != "credential_env"}).upper().replace("SHA256", "")
