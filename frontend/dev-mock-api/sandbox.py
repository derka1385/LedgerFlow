"""Fail-closed Docker runner used by the DEV MOCK API and containment benchmark.

Writable storage is private tmpfs: /work (128 MiB / 4096 inodes, including
TMPDIR) and /dev/shm (1 MiB). No writable host directory is exposed.
The container stays alive during bounded artifact extraction, because tmpfs
disappears on stop. All paths, limits and collection code are host policy.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path, PurePosixPath

IMAGE = os.environ.get("LEDGERFLOW_SANDBOX_IMAGE", "python:3.12-slim")
DEADLINE_S = int(os.environ.get("LEDGERFLOW_SANDBOX_TIMEOUT", "30"))
WORK_BYTES = 128 * 1024 * 1024
WORK_INODES = 4096
SHM_BYTES = 1024 * 1024
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
MAX_REPORT_BYTES = 1024 * 1024
LOG_BYTES = 20000
FLAGS = ["--network", "none", "--read-only", "--cpus", "1", "--memory", "512m",
         "--memory-swap", "512m", "--pids-limit", "128", "--cap-drop", "ALL",
         "--security-opt", "no-new-privileges", "--user", "10001:10001",
         "--ulimit", "core=0:0", "--ulimit", "nofile=256:256",
         "--shm-size", str(SHM_BYTES), "--log-driver", "none",
         "--tmpfs", f"/work:rw,nosuid,nodev,noexec,size={WORK_BYTES},nr_inodes={WORK_INODES},uid=10001,gid=10001,mode=0700"]


def docker_available() -> bool:
    try:
        return subprocess.run(["docker", "info"], capture_output=True, timeout=5).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def image_available() -> bool:
    try:
        return subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _capture(cmd: list[str], timeout: float) -> tuple[int, str, str]:
    """Drain both pipes continuously, retaining only bounded tails in memory."""
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    tails = [bytearray(), bytearray()]

    def drain(pipe, buf):
        try:
            while chunk := pipe.read(8192):
                buf.extend(chunk)
                del buf[:-LOG_BYTES]
        finally:
            pipe.close()

    threads = [threading.Thread(target=drain, args=(pipe, buf), daemon=True)
               for pipe, buf in zip((proc.stdout, proc.stderr), tails)]
    for thread in threads:
        thread.start()
    timed_out = False
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        timed_out = True
    finally:
        for thread in threads:
            thread.join(timeout=2)
    if timed_out:
        # Keep the bounded output collected before the deadline. The caller still
        # destroys the container and discards all candidate artifacts on timeout.
        raise subprocess.TimeoutExpired(cmd, timeout, output=bytes(tails[0]).decode("utf-8", errors="replace"), stderr=bytes(tails[1]).decode("utf-8", errors="replace"))
    return proc.returncode, *(bytes(buf).decode("utf-8", errors="replace") for buf in tails)


# Isolated Python ignores generated /input modules and PYTHONPATH. O_NOFOLLOW,
# nonblocking open, fstat and limit+1 prevent symlink/FIFO/oversized artifacts.
COLLECT = r'''
import base64, json, os, stat
result = {}
for name, limit in (("candidate.xlsx", 16777216), ("report.json", 1048576)):
    try:
        fd = os.open("/work/" + name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        continue
    with os.fdopen(fd, "rb") as f:
        st = os.fstat(f.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_size > limit:
            raise ValueError("invalid or oversized artifact: " + name)
        data = f.read(limit + 1)
        if len(data) > limit:
            raise ValueError("artifact grew beyond limit: " + name)
    result[name] = base64.b64encode(data).decode("ascii")
print(json.dumps(result))
'''


def run(inputs: dict[str, bytes], entry: str = "main.py", on_event=None, deadline_s: int = DEADLINE_S) -> dict:
    """Run relative input files; return bounded artifacts only after full cleanup."""
    for rel in (*inputs, entry):
        p = PurePosixPath(rel)
        if p.is_absolute() or ".." in p.parts or not p.parts:
            raise ValueError("sandbox input paths must be relative without traversal")
    if entry not in inputs:
        raise ValueError("entry must be an input")
    if sum(map(len, inputs.values())) > 32 * 1024 * 1024 or len(inputs) > 1024:
        raise ValueError("sandbox input budget exceeded")
    emit = on_event or (lambda *_: None)
    result = {"runtime": "none", "sandbox_id": None, "exit_code": None,
              "termination_reason": "sandbox_unavailable", "stdout": "", "stderr": "",
              "duration_ms": 0, "peak_memory_bytes": None, "output": None, "report": None,
              "destroyed": True, "limits": None}
    if not (docker_available() and image_available()):
        result["stderr"] = f"Docker or image {IMAGE!r} unavailable; refusing unsandboxed execution."
        return result
    limits = {"cpus": 1, "memory_mb": 512, "timeout_s": deadline_s, "pids": 128,
              "network": "none", "work_bytes": WORK_BYTES, "work_inodes": WORK_INODES,
              "shm_bytes": SHM_BYTES, "temporary_directory": "/work/.tmp"}
    name = f"lf_run_{uuid.uuid4().hex[:12]}"
    root = Path(tempfile.mkdtemp(prefix="lf_sbx_"))
    t0 = time.monotonic()
    result.update(runtime="docker", sandbox_id=name, limits=limits)
    try:
        # Docker on Linux must traverse these directories as the workload uid.
        os.chmod(root, 0o755)
        for rel, data in inputs.items():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
            p.chmod(0o444)
        cmd = ["docker", "run", "-d", "--name", name, *FLAGS,
               "-e", "PYTHONPATH=/input", "-e", "TMPDIR=/work/.tmp",
               "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "HOME=/work",
               "--mount", f"type=bind,src={root},dst=/input,readonly",
               "-w", "/work", "--entrypoint", "python3", IMAGE, "-I", "-c",
               f"import time; time.sleep({max(1, deadline_s) + 60})"]
        started = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if started.returncode:
            raise RuntimeError(started.stderr[-LOG_BYTES:])
        emit("sandbox.created", {"sandbox_id": name, "runtime": "docker", "image": IMAGE, "limits": limits})
        subprocess.run(["docker", "exec", name, "python3", "-I", "-c",
                        "import os; os.mkdir('/work/.tmp', 0o700)"],
                       check=True, capture_output=True, timeout=10)
        emit("sandbox.started", {"sandbox_id": name})
        result["exit_code"], result["stdout"], result["stderr"] = _capture(
            ["docker", "exec", name, "python3", "-u", f"/input/{entry}"], deadline_s)
        result["termination_reason"] = "exited"
        if result["exit_code"] == 0:
            artifacts = subprocess.run(["docker", "exec", name, "python3", "-I", "-c", COLLECT],
                                       capture_output=True, timeout=10)
            if artifacts.returncode:
                raise RuntimeError(artifacts.stderr.decode(errors="replace")[-LOG_BYTES:])
            data = json.loads(artifacts.stdout)
            if "candidate.xlsx" in data:
                result["output"] = base64.b64decode(data["candidate.xlsx"], validate=True)
            if "report.json" in data:
                result["report"] = base64.b64decode(data["report.json"], validate=True).decode("utf-8")
    except subprocess.TimeoutExpired as exc:
        result.update(termination_reason="timeout", output=None, report=None,
                      stdout=exc.output if isinstance(exc.output, str) else "",
                      stderr=exc.stderr if isinstance(exc.stderr, str) else "")
    except Exception as exc:
        result.update(termination_reason="sandbox_error", stderr=str(exc)[-LOG_BYTES:], output=None, report=None)
    finally:
        try:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=10)
            check = subprocess.run(["docker", "container", "inspect", name], capture_output=True, timeout=10)
            # Inspect failure alone could mean daemon failure; confirm daemon health.
            result["destroyed"] = check.returncode != 0 and docker_available()
        except (OSError, subprocess.TimeoutExpired):
            result["destroyed"] = False
        shutil.rmtree(root)
        result["duration_ms"] = int((time.monotonic() - t0) * 1000)
    if not result["destroyed"]:
        result.update(output=None, report=None, termination_reason="cleanup_failed")
    return result
