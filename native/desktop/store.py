"""Local SQLite snapshots of the existing reference runtime, without pickle or credentials."""
import base64
import hashlib
import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path


def encode(value):
    if isinstance(value, bytes):
        return {"bytes": base64.b64encode(value).decode("ascii")}
    if isinstance(value, dict):
        return {"map": [[encode(k), encode(v)] for k, v in value.items()]}
    if isinstance(value, tuple):
        return {"tuple": [encode(v) for v in value]}
    if isinstance(value, list):
        return [encode(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(type(value).__name__)


def decode(value):
    if isinstance(value, list):
        return [decode(v) for v in value]
    if isinstance(value, dict):
        if set(value) == {"bytes"}:
            return base64.b64decode(value["bytes"], validate=True)
        if set(value) == {"tuple"}:
            return tuple(decode(v) for v in value["tuple"])
        if set(value) == {"map"}:
            return {decode(k): decode(v) for k, v in value["map"]}
        raise ValueError("Invalid snapshot value")
    return value


class Store:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(directory, 0o700)
        self.path = directory / "workspace.sqlite3"
        self.lock = threading.Lock()
        with self.connection() as db:
            db.execute("CREATE TABLE IF NOT EXISTS snapshot (id INTEGER PRIMARY KEY CHECK(id=1), payload BLOB NOT NULL, sha TEXT NOT NULL)")
        os.chmod(self.path, 0o600)

    @contextmanager
    def connection(self):
        connection=sqlite3.connect(self.path, timeout=15)
        try:
            with connection: yield connection
        finally: connection.close()

    def load(self):
        with self.connection() as db:
            row = db.execute("SELECT payload, sha FROM snapshot WHERE id=1").fetchone()
        if not row:
            return None
        payload, digest = row
        if hashlib.sha256(payload).hexdigest() != digest:
            raise ValueError("Local workspace checksum failed; keep the database for recovery.")
        return decode(json.loads(payload))

    def save(self, state):
        payload = json.dumps(encode(state), ensure_ascii=True, separators=(",", ":")).encode()
        with self.lock, self.connection() as db:
            db.execute("INSERT OR REPLACE INTO snapshot(id,payload,sha) VALUES(1,?,?)", (payload, hashlib.sha256(payload).hexdigest()))
