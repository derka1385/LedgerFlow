"""Capture real-runtime security evidence without overwriting benchmark baselines.

Run on the target host: python3 benchmark/security_evidence.py --host-label vultr-INSTANCE
Requires Docker and the configured sandbox image. Never makes inference requests.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import bench
import sandbox


def command(args):
    p = subprocess.run(args, capture_output=True, text=True, timeout=30)
    return {"command": args, "exit_code": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-label", required=True, help="Operator-supplied identity; not provider attestation")
    parser.add_argument("--output", type=Path, default=bench.RESULTS / "security-evidence.json")
    args = parser.parse_args()
    if not (sandbox.docker_available() and sandbox.image_available()):
        parser.error("Docker/image unavailable: no containment result can be claimed")
    evidence = {"schema": "ledgerflow.security-evidence.v1", "started_at": datetime.now(timezone.utc).isoformat(),
                "host_label_operator_supplied": args.host_label, "system": platform.platform(),
                "source_sha256": {}, "runtime": command(["docker", "version"]),
                "daemon": command(["docker", "info", "--format", "{{json .}}"]),
                "image": command(["docker", "image", "inspect", sandbox.IMAGE,
                                  "--format", "{{json .RepoDigests}} {{.Id}}"])}
    for rel in ("frontend/dev-mock-api/sandbox.py", "benchmark/faults.py", "benchmark/bench.py",
                "benchmark/security_evidence.py", "frontend/dev-mock-api/test_sandbox.py"):
        evidence["source_sha256"][rel] = hashlib.sha256((bench.REPO / rel).read_bytes()).hexdigest()

    def observe(kind, data):
        if kind == "sandbox.created":
            # Inspect the actual live container, including mounts, namespace,
            # seccomp/runtime, resource settings and environment variable names.
            p = command(["docker", "inspect", data["sandbox_id"]])
            cfg = json.loads(p["stdout"])[0]
            evidence["container_configuration"] = {
                k: cfg[k] for k in ("Id", "Image", "HostConfig", "Mounts", "AppArmorProfile") if k in cfg}
            evidence["container_configuration"]["environment_names"] = sorted(
                e.split("=", 1)[0] for e in cfg["Config"].get("Env", []))

    evidence["filesystem_observation"] = sandbox.run({"main.py": b'''
import json, os, tempfile
print(json.dumps({'uid': os.getuid(), 'gid': os.getgid(), 'tempdir': tempfile.gettempdir(),
                  'work_capacity': os.statvfs('/work').f_blocks * os.statvfs('/work').f_frsize,
                  'work_inodes': os.statvfs('/work').f_files}))
print(open('/proc/self/mountinfo').read())
print(open('/proc/self/status').read())
'''}, on_event=observe)
    listener = bench.Listener()
    try:
        control = bench.control_connect(listener)
        evidence["network_positive_control"] = control
        evidence["containment"] = bench.s_containment(listener, control)
    finally:
        listener.sock.close()
    evidence["storage_regressions"] = command([
        sys.executable, "-m", "pytest", "-q", "-rs", str(bench.MOCK_API / "test_sandbox.py")])
    evidence["legitimate_excel"] = bench.s_codegen_mock()
    evidence["workbook_preservation"] = bench.s_preservation()
    evidence["finished_at"] = datetime.now(timezone.utc).isoformat()
    evidence["passed"] = (evidence["containment"]["metrics"]["contained"] == 13
                          and control["reached_listener"]
                          and evidence["storage_regressions"]["exit_code"] == 0
                          and evidence["legitimate_excel"]["status"] == "pass"
                          and evidence["workbook_preservation"]["status"] == "pass")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, default=str) + "\n")
    print(f"Evidence: {args.output}; passed={evidence['passed']}")
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
