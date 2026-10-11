"""Unit tests for the canonical ops-artifact schema (audit finding F3/F4)."""

import pytest

from src.ops.artifacts import (
    CONFIRMED_FILL_STATUSES,
    extract_fills,
    is_confirmed_fill,
    make_fill_record,
    sleeve_of,
)


def _fill(**overrides):
    base = {
        "client_order_id": "run-sleeve-AAPL-0",
        "sleeve_id": "sleeve",
        "status": "FILLED",
        "ticker": "AAPL",
        "side": "buy",
        "qty": 1.0,
        "avg_px": 150.0,
    }
    base.update(overrides)
    return base


def test_extract_fills_accepts_wrapper():
    doc = {"run_id": "r1", "fills": [_fill()]}
    assert extract_fills(doc) == [_fill()]


def test_extract_fills_accepts_bare_list():
    assert extract_fills([_fill()]) == [_fill()]


def test_extract_fills_rejects_dict_without_fills():
    with pytest.raises(ValueError):
        extract_fills({"run_id": "r1"})


def test_extract_fills_rejects_non_list_fills():
    with pytest.raises(ValueError):
        extract_fills({"run_id": "r1", "fills": {"a": 1}})


def test_extract_fills_rejects_missing_required_fields():
    bad = _fill()
    del bad["sleeve_id"]
    with pytest.raises(ValueError):
        extract_fills({"run_id": "r1", "fills": [bad]})


def test_extract_fills_rejects_unknown_status():
    with pytest.raises(ValueError):
        extract_fills({"run_id": "r1", "fills": [_fill(status="WEIRD")]})


def test_extract_fills_rejects_missing_artifact():
    with pytest.raises(ValueError):
        extract_fills(None)


def test_is_confirmed_fill_requires_status_and_price():
    assert is_confirmed_fill(_fill()) is True
    assert is_confirmed_fill(_fill(status="PARTIAL")) is True
    assert is_confirmed_fill(_fill(status="SUBMITTED")) is False
    assert is_confirmed_fill(_fill(status="UNKNOWN")) is False
    assert is_confirmed_fill(_fill(avg_px=None)) is False
    assert is_confirmed_fill("not a dict") is False


def test_sleeve_of_canonical_then_legacy():
    assert sleeve_of({"sleeve_id": "new"}) == "new"
    assert sleeve_of({"sleeve": "old"}) == "old"
    assert sleeve_of({"sleeve_id": "new", "sleeve": "old"}) == "new"
    assert sleeve_of({}) is None


def test_make_fill_record_shape():
    rec = make_fill_record(
        client_order_id="c1", sleeve_id="s1", ticker="SPY", side="buy",
        qty=2, status="FILLED", avg_px=600.0, ts="2026-10-11T00:00:00Z",
    )
    assert rec["sleeve_id"] == "s1"
    assert rec["status"] in CONFIRMED_FILL_STATUSES
    assert rec["avg_px"] == 600.0
    for field in ("client_order_id", "sleeve_id", "status", "ticker", "side", "qty"):
        assert field in rec
