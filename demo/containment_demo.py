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
mount_probe = """from os import ST_RDONLY, statvfs
for mount in ("/", "/input"):
    print(f"PROBE mount {mount} read_only: {bool(statvfs(mount).f_flag & ST_RDONLY)}")
"""
r = sandbox.run({"main.py": (mount_probe + programs.CONTAINMENT_PROBE).encode()}, deadline_s=10)
for line in (r["stdout"] + r["stderr"]).splitlines():
    if line.startswith("PROBE"):
        print("  " + line)
lines = r["stdout"] + r["stderr"]
# gVisor may check directory permissions before returning EROFS.
write_denied = all(
    any(
        line.startswith(f"PROBE filesystem {path} :")
        and ("[Errno 13]" in line or "[Errno 30]" in line)
        for line in lines.splitlines()
    )
    for path in ("/etc/ledgerflow_probe", "/input/overwrite_attempt")
)
ok = (r["runtime"] == "docker" and r["termination_reason"] == "timeout" and r["destroyed"]
      and "Network is unreachable" in lines and "CONNECTED" not in lines and "WRITTEN" not in lines
      and "PROBE mount / read_only: True" in lines and "PROBE mount /input read_only: True" in lines
      and "PROBE run_secrets_exists: False" in lines and "VULTR_INFERENCE_API_KEY" not in lines
      and write_denied)
print(f"\nruntime={r['runtime']} termination={r['termination_reason']} after {r['duration_ms']} ms, container destroyed={r['destroyed']}")
print("RESULT: CONTAINED" if ok else "RESULT: NOT CONTAINED - stop the demo and investigate")
sys.exit(0 if ok else 1)
