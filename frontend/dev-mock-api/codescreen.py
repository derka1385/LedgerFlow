"""Static screen of generated code before it runs (product/VALIDATION.md V-SEC-02).

Not the security boundary (the sandbox is). It refuses obviously hostile or
out-of-contract programs early and produces a readable security event.
"""
from __future__ import annotations

import ast

DENIED_MODULES = {"socket", "subprocess", "requests", "urllib", "http", "ctypes", "shutil", "multiprocessing", "ftplib",
                  "smtplib", "telnetlib", "asyncio", "importlib", "pty", "signal"}
DENIED_CALLS = {"eval", "exec", "compile", "__import__", "system", "popen", "spawn", "execv", "execve", "fork", "kill"}
ALLOWED_PATH_PREFIXES = ("/input/", "/work/")


def screen(code: str) -> list[str]:
    """Return a list of findings; empty means the program may run."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"syntax error: {e.msg} (line {e.lineno})"]
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            for n in names:
                if n.split(".")[0] in DENIED_MODULES:
                    out.append(f"line {node.lineno}: imports {n}")
        elif isinstance(node, ast.Call):
            f = node.func
            name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""
            if name in DENIED_CALLS:
                out.append(f"line {node.lineno}: calls {name}()")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith("/"):
            if not node.value.startswith(ALLOWED_PATH_PREFIXES) and node.value not in ("/input", "/work"):
                out.append(f"line {node.lineno}: path outside /input and /work: {node.value[:60]!r}")
    return out
