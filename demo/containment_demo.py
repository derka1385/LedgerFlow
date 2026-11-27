"""Sandbox containment demonstration (real Docker, no fallback). python3 demo/containment_demo.py

Runs the same fixed hostile probe as the app's Security page in a fresh sandbox container: it tries the network,
writes outside its scratch space, looks for secrets, then loops forever until the host kills it. Prints what the
runtime actually returned. Refuses to run without Docker; it never executes the probe on the host.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "frontend" / "dev-mock-api"))
import programs  # noqa: E402
import sandbox  # noqa: E402

if not (sandbox.docker_available() and sandbox.image_available()):
    sys.exit(f"Docker or the sandbox image {sandbox.IMAGE} is not available: start Docker Desktop first. Nothing was run.")
print(f"Sandbox flags: {' '.join(sandbox.FLAGS)}\nRunning the hostile probe (deadline 10 s)...\n")
r = sandbox.run({"main.py": programs.CONTAINMENT_PROBE.encode()}, deadline_s=10)
for line in (r["stdout"] + r["stderr"]).splitlines():
    if line.startswith("PROBE"):
        print("  " + line)
lines = r["stdout"] + r["stderr"]
ok = (r["runtime"] == "docker" and r["termination_reason"] == "timeout" and r["destroyed"]
      and "Network is unreachable" in lines and "Read-only file system" in lines and "CONNECTED" not in lines and "WRITTEN" not in lines)
print(f"\nruntime={r['runtime']} termination={r['termination_reason']} after {r['duration_ms']} ms, container destroyed={r['destroyed']}")
print("RESULT: CONTAINED" if ok else "RESULT: NOT CONTAINED - stop the demo and investigate")
sys.exit(0 if ok else 1)
