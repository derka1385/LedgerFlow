"""Boundary regression checks; real runtime checks skip explicitly without Docker."""
import errno
import json
import subprocess
import sys
from unittest.mock import patch

import pytest

import sandbox


def test_timeout_preserves_bounded_diagnostics():
    # Fixed diagnostic fixture, not model-generated accounting code.
    with pytest.raises(subprocess.TimeoutExpired) as error:
        sandbox._capture([sys.executable, "-u", "-c", "import time; print('before timeout', flush=True); time.sleep(10)"], .25)
    assert "before timeout" in error.value.output


@pytest.mark.parametrize("path", ["../escape", "/etc/escape", "nested/../../escape"])
def test_reject_input_traversal(path):
    with pytest.raises(ValueError):
        sandbox.run({path: b"x", "main.py": b"pass"})


def test_no_unsandboxed_fallback(monkeypatch):
    monkeypatch.setenv("LEDGERFLOW_ALLOW_UNSANDBOXED", "1")
    with patch.object(sandbox, "docker_available", return_value=False):
        result = sandbox.run({"main.py": b"raise AssertionError('must never execute')"})
    assert result["termination_reason"] == "sandbox_unavailable"
    assert result["runtime"] == "none" and result["output"] is None


runtime = pytest.mark.skipif(not (sandbox.docker_available() and sandbox.image_available()),
                             reason="Real Docker daemon and sandbox image required")


@runtime
def test_aggregate_quota_and_temporary_isolation():
    # Multiple files in both directories must consume ONE quota, not per-file limits.
    code = '''
import errno, json, os, tempfile
print("TEMP", tempfile.gettempdir(), flush=True)
written = 0
try:
    for i in range(256):
        path = ("/work/" if i % 2 else tempfile.gettempdir() + "/") + str(i)
        with open(path, "wb", buffering=0) as f:
            written += f.write(b"x" * 1024 * 1024)
except OSError as e:
    print("QUOTA", json.dumps({"errno": e.errno, "written": written}), flush=True)
'''
    result = sandbox.run({"main.py": code.encode()})
    assert result["exit_code"] == 0 and result["destroyed"]
    assert "TEMP /work/.tmp" in result["stdout"]
    quota = json.loads(next(l[6:] for l in result["stdout"].splitlines() if l.startswith("QUOTA ")))
    assert quota["errno"] == errno.ENOSPC
    assert 0 < quota["written"] <= sandbox.WORK_BYTES
    fresh = sandbox.run({"main.py": b"import os; print('FRESH', os.listdir('/work/.tmp'))"})
    assert "FRESH []" in fresh["stdout"] and fresh["destroyed"]


@runtime
def test_inode_quota():
    result = sandbox.run({"main.py": b'''
import errno
try:
    for i in range(10000):
        open('/work/file' + str(i), 'wb').close()
except OSError as e:
    print('INODES', e.errno, i)
'''})
    assert result["exit_code"] == 0 and result["destroyed"]
    assert f"INODES {errno.ENOSPC} " in result["stdout"]


@runtime
@pytest.mark.parametrize("action", [
    "os.symlink('/input/main.py', '/work/candidate.xlsx')",
    "os.mkfifo('/work/candidate.xlsx')",
    f"f = open('/work/candidate.xlsx', 'wb'); f.truncate({sandbox.MAX_OUTPUT_BYTES + 1}); f.close()",
])
def test_reject_unsafe_artifacts(action):
    result = sandbox.run({"main.py": ("import os\n" + action).encode()})
    assert result["termination_reason"] == "sandbox_error"
    assert result["output"] is None and result["destroyed"]


@runtime
def test_collect_regular_artifact_and_tempfile():
    result = sandbox.run({"main.py": b'''
import tempfile
with tempfile.NamedTemporaryFile() as f:
    f.write(b'Excel temporary data'); f.flush()
    open('/work/candidate.xlsx', 'wb').write(b'candidate bytes')
open('/work/report.json', 'w').write('{"ok": true}')
'''})
    assert result["exit_code"] == 0 and result["destroyed"]
    assert result["output"] == b"candidate bytes"
    assert json.loads(result["report"]) == {"ok": True}
