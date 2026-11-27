from __future__ import annotations

import pytest

from ledgerflow.domain.canonical import NonCanonicalValue, canonical_json, canonical_sha256


def test_keys_are_sorted_and_separators_compact() -> None:
    assert canonical_json({"b": 1, "a": [2, 1]}) == '{"a":[2,1],"b":1}'


def test_hash_is_independent_of_insertion_order() -> None:
    assert canonical_sha256({"x": 1, "y": "é"}) == canonical_sha256({"y": "é", "x": 1})


def test_excluded_self_hash_field_does_not_change_digest() -> None:
    body = {"amount_minor": 12500, "currency": "SEK"}
    with_hash = {**body, "sha256": "ignored"}
    assert canonical_sha256(with_hash, exclude={"sha256"}) == canonical_sha256(body)


def test_non_ascii_is_kept_as_utf8_text() -> None:
    assert canonical_json({"merchant": "Åhléns"}) == '{"merchant":"Åhléns"}'


@pytest.mark.parametrize("value", [1.5, {"amount": 0.1}, [1, 2.0], float("nan")])
def test_floats_are_rejected(value: object) -> None:
    with pytest.raises(NonCanonicalValue):
        canonical_json(value)


def test_integers_including_zero_are_accepted() -> None:
    assert canonical_json({"minor": 0, "flag": True}) == '{"flag":true,"minor":0}'


def test_non_string_keys_are_rejected() -> None:
    with pytest.raises(NonCanonicalValue):
        canonical_json({1: "one"})
