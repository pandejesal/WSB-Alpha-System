"""R2 regression guard (RG-1): 5 read-only tests.

All tests use tmp_path fixtures or in-memory objects only — the real
``strategies/registry.json``, committed ``docs/data`` evals, gates,
thresholds, commission values, killswitch, execution, live flags and
``.github`` are never touched.
"""

import inspect
import json
import os

import pytest
import yaml


def test_rg1_killswitch_dual_gate_fail_closed():
    # (1) KillSwitch fail-closed strings present + dual-gate disagreement denied.
    import src.ops.killswitch as ks_mod

    source = inspect.getsource(ks_mod)
    assert "Failing closed" in source
    assert "fail-closed" in source or "fail closed" in source.lower()

    from src.ops.killswitch import KillSwitch, dual_gate_allows_trading

    # Missing state file fails closed (never tradable).
    ks = KillSwitch(filepath=os.path.join("nonexistent_dir_xyz", "ops_state.yaml"))
    assert ks.get_state() == "halt_new_orders"
    assert ks.can_trade() is False

    # Disagreement (killswitch halted, live flag on) is denied and named.
    allowed, reason = dual_gate_allows_trading(
        True, filepath=os.path.join("nonexistent_dir_xyz", "ops_state.yaml")
    )
    assert allowed is False
    assert "disagreement" in reason


def test_rg2_record_registry_path_is_id_keyed(tmp_path):
    # (2) The record registry path goes through _locked_registry_update and
    # is id-keyed: two fixture specs, same family, distinct ids -> two rows,
    # first row untouched. tmp_path registry only.
    import src.ops.preregistration as prereg
    from src.ops.preregistration import _locked_registry_update

    assert "_locked_registry_update" in inspect.getsource(prereg.record_evaluation)

    registry_path = str(tmp_path / "registry.json")
    with open(registry_path, "w") as f:
        json.dump({"strategies": []}, f)

    spec_a = {"id": "rg2-a", "name": "RG2 A", "family": "rg2fam"}
    spec_b = {"id": "rg2-b", "name": "RG2 B", "family": "rg2fam"}
    _locked_registry_update(registry_path, spec_a, "spec_a.yaml", "rg2fam", "FAIL", "eval_a.json")
    with open(registry_path) as f:
        first_row = json.load(f)["strategies"][0]
    assert first_row["id"] == "rg2-a"

    _locked_registry_update(registry_path, spec_b, "spec_b.yaml", "rg2fam", "FAIL", "eval_b.json")
    with open(registry_path) as f:
        rows = json.load(f)["strategies"]
    assert len(rows) == 2
    assert rows[0] == first_row
    assert rows[1]["id"] == "rg2-b"


def test_rg3_eval_versioning_keeps_first_byte_identical(tmp_path):
    # (3) Two records for the same family+cycle -> two files; the first file
    # stays byte-identical.
    from src.ops.preregistration import freeze_preregistration, record_evaluation

    docs_dir = str(tmp_path / "docs")
    os.makedirs(docs_dir, exist_ok=True)
    registry_path = str(tmp_path / "registry.json")
    spec_path = str(tmp_path / "spec.yaml")
    with open(spec_path, "w") as f:
        yaml.dump({"id": "rg3", "name": "RG3", "family": "rg3fam"}, f)

    freeze_preregistration(spec_path, "RG-3 claim", cycle=1, docs_dir=docs_dir)
    first = record_evaluation(spec_path, "FAIL", cycle=1, registry_path=registry_path, docs_dir=docs_dir)
    with open(first, "rb") as f:
        first_bytes = f.read()

    second = record_evaluation(spec_path, "FAIL", cycle=1, registry_path=registry_path, docs_dir=docs_dir)
    assert second != first
    assert os.path.exists(first) and os.path.exists(second)
    with open(first, "rb") as f:
        assert f.read() == first_bytes


def test_rg4_default_never_backfills_leading_nan():
    # (4) Market-data default fill never backfills leading NaN; the
    # tradability guard rejects an all-zero frame.
    import pandas as pd

    from src.data.market_data import MarketDataManager
    from src.data.price_guards import assert_tradable_prices

    mgr = MarketDataManager(provider=object())
    df = pd.DataFrame({"close": [float("nan"), float("nan"), 100.0, 101.0]})
    out = mgr._apply_fill_policy(df, "RG4", "ffill_only")
    assert pd.isna(out["close"].iloc[0])
    assert pd.isna(out["close"].iloc[1])
    assert out["close"].iloc[2] == 100.0

    with pytest.raises(ValueError, match="all-zero"):
        assert_tradable_prices(pd.DataFrame({"close": [0.0] * 5}), symbol="RG4")


def test_rg5_commission_refs_intact():
    # (5) Commission references intact: canonical 1.0bp, operational 2.5bp.
    from config.risk_config import CANONICAL_COMMISSION_BPS

    import evolve_real

    assert CANONICAL_COMMISSION_BPS == 1.0
    assert evolve_real.COST_COMMISSION_BPS == 2.5
