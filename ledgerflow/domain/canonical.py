"""Canonical JSON and SHA-256 helpers (DATA_SCHEMAS conventions).

Canonical form: UTF-8, sorted keys, compact separators, no floats, no NaN.
Money and counters are integers, so floats are rejected rather than coerced.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any


class NonCanonicalValue(ValueError):
    """Raised when a value cannot be encoded in canonical form."""


def _reject_floats(value: Any, path: str = "$") -> None:
    if type(value) is float:  # bool is a subclass of int, and float is never allowed
        raise NonCanonicalValue(f"float at {path}; use integer minor units")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise NonCanonicalValue(f"non-string key at {path}")
            _reject_floats(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_floats(item, f"{path}[{index}]")


def canonical_json(value: Any, *, exclude: Iterable[str] = ()) -> str:
    """Return canonical JSON text. `exclude` drops top-level keys, e.g. a self-hash field."""
    if isinstance(value, dict) and exclude:
        skipped = set(exclude)
        value = {key: item for key, item in value.items() if key not in skipped}
    _reject_floats(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def canonical_sha256(value: Any, *, exclude: Iterable[str] = ()) -> str:
    return sha256_hex(canonical_json(value, exclude=exclude))
