import os
import json
import yaml
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock
import scripts

# Synthetic data generator
def create_synthetic_data(tickers=["T1", "T2", "T3"], rows=400):
    np.random.seed(42)
    dfs = []
    dates = pd.date_range(end="2023-12-31", periods=rows, freq="B")

    for t in tickers:
        df = pd.DataFrame(index=dates)
        df["Date"] = df.index
        df["Date_str"] = df.index.astype(str)
        df["post_date"] = df.index
        df["Ticker"] = t
        returns = np.random.normal(0.0005, 0.01, rows)
        prices = 100 * np.exp(returns.cumsum())
        df["Close"] = prices
        df["Open"] = prices * np.random.normal(1.0, 0.005, rows)
        df["High"] = df[["Open", "Close"]].max(axis=1) * np.random.normal(1.005, 0.002, rows)
        df["Low"] = df[["Open", "Close"]].min(axis=1) * np.random.normal(0.995, 0.002, rows)
        df["Volume"] = np.random.randint(100000, 1000000, rows)
        dfs.append(df)

    combined = pd.concat(dfs, ignore_index=True)

    # Validation engine base data expects specific format
    posts_data = []
    for d in dates:
        posts_data.append({"post_date": d, "ticker": "T1", "sentiment_score": 0.5, "post_id": str(d)})
    posts_df = pd.DataFrame(posts_data)

    stock_dfs = {t: combined[combined["Ticker"] == t].copy() for t in tickers}
    spy_close = combined[combined["Ticker"] == tickers[0]]["Close"].copy()

    return combined, posts_df, stock_dfs, spy_close

# Test 1: run_permutation_study
@patch("scripts.run_permutation_study.load_base_data")
@patch("scripts.run_permutation_study.run_in_sample_test")
@patch("scripts.run_permutation_study.run_walk_forward_test")
def test_run_permutation_study_synthetic(mock_wf, mock_is, mock_load, tmp_path):
    mock_load.return_value = (MagicMock(), MagicMock(), MagicMock())
    mock_is.return_value = (0.1, 1.5, [], [], 0.04, None, None)
    mock_wf.return_value = (0.1, 1.5, [], [], 0.03, 0.6, None)

    real_write_artifact = scripts.run_permutation_study.write_artifact
    out_file = tmp_path / "permutation_study.json"
    real_path = os.path.abspath("docs/data/permutation_study.json")
    with open(real_path, "r") as f:
        real_before = f.read()
    scripts.run_permutation_study.write_artifact = lambda path, payload: real_write_artifact(str(out_file), payload)

    try:
        from scripts.run_permutation_study import run_study
        run_study()
    finally:
        scripts.run_permutation_study.write_artifact = real_write_artifact

    with open(real_path, "r") as f:
        real_after = f.read()

    assert real_before == real_after, "real docs/data/permutation_study.json was modified by the test"
    assert out_file.exists()
    with open(out_file, "r") as f:
        data = json.load(f)

    assert data["status"] == "success"
    assert "in_sample_p_value" in data
    assert data["permutations"] == 200

# Test 2: evaluate_candidate.py on ta_rules
@patch("scripts.evaluate_candidate.run_in_sample_test")
@patch("scripts.evaluate_candidate.run_walk_forward_test")
@patch("scripts.evaluate_candidate.get_provider")
def test_evaluate_candidate_ta_rules(mock_get_provider, mock_wf, mock_is, tmp_path):
    mock_is.return_value = (0.1, 1.5, [0.1], [1.5], 0.04, None, None)
    mock_wf.return_value = (0.1, 1.5, [0.1], [1.5], 0.03, 0.6, 10)
    combined, _, _, _ = create_synthetic_data()

    mock_provider = MagicMock()
    mock_provider.fetch_ohlcv.return_value = combined
    mock_get_provider.return_value = mock_provider

    spec_path = tmp_path / "ta_spec.yaml"
    eval_path = tmp_path / "eval_ta.json"
    prereg_path = tmp_path / "prereg_ta.md"

    spec = {
        "id": "test_ta",
        "name": "Test TA",
        "family": "ta_rules",
        "universe": "SPY",
        "parameters": {},
        "signal": {
            "entry": "ema_cross",
            "fast_ma": 10,
            "slow_ma": 20
        },
        "pre_registration_ref": str(prereg_path),
        "eval_records": str(eval_path)
    }

    with open(spec_path, "w") as f:
        yaml.dump(spec, f)

    import sys
    from scripts.evaluate_candidate import main

    test_args = ["evaluate_candidate.py", str(spec_path), "--tickers", "T1,T2", "--days", "100"]
    with patch.object(sys, 'argv', test_args):
        main()

    assert eval_path.exists()
    with open(eval_path, "r") as f:
        data = json.load(f)
    assert data["family"] == "ta_rules"
    assert data["status"] == "evaluated"
    assert "dsr" in data

    assert prereg_path.exists()

# Test 3: evaluate_candidate.py on multi_factor
def test_evaluate_candidate_multi_factor(tmp_path):
    spec_path = tmp_path / "mf_spec.yaml"
    eval_path = tmp_path / "eval_mf.json"
    prereg_path = tmp_path / "prereg_mf.md"

    spec = {
        "id": "test_mf",
        "name": "Test MF",
        "universe": "SPY",
        "family": "multi_factor",
        "parameters": {},
        "signal": {"entry": "mock", "exit": "mock"},
        "pre_registration_ref": str(prereg_path),
        "eval_records": str(eval_path)
    }

    with open(spec_path, "w") as f:
        import yaml
        yaml.dump(spec, f)

    import sys
    from scripts.evaluate_candidate import main

    test_args = ["evaluate_candidate.py", str(spec_path), "--tickers", "T1,T2", "--days", "100"]
    with patch.object(sys, 'argv', test_args):
        try:
            main()
        except SystemExit as e:
            assert e.code == 0

    assert eval_path.exists()
    with open(eval_path, "r") as f:
        import json
        data = json.load(f)

    assert data["family"] == "multi_factor"
    assert data["verdict"] == "HONEST_ABANDON"
    assert data["status"] == "not_evaluable_missing_plumbing"

def test_evaluate_candidate_xgboost_exits_honest_abandon(tmp_path):
    spec_path = tmp_path / "xgb_spec.yaml"
    eval_path = tmp_path / "eval_xgb.json"
    prereg_path = tmp_path / "prereg_xgb.md"

    spec = {
        "id": "test_xgb",
        "name": "Test XGB",
        "universe": "SPY",
        "family": "xgboost_exits",
        "parameters": {"entry": 10},
        "signal": {"entry": "buy SPY when RSI(2) < 10", "exit": "ml"},
        "pre_registration_ref": str(prereg_path),
        "eval_records": str(eval_path)
    }

    with open(spec_path, "w") as f:
        import yaml
        yaml.dump(spec, f)

    import sys
    from scripts.evaluate_candidate import main

    test_args = ["evaluate_candidate.py", str(spec_path), "--tickers", "SPY", "--days", "100"]
    with patch.object(sys, 'argv', test_args):
        try:
            main()
        except SystemExit as e:
            assert e.code == 0

    assert eval_path.exists()
    with open(eval_path, "r") as f:
        import json
        data = json.load(f)

    assert data["family"] == "xgboost_exits"
    assert data["verdict"] == "HONEST_ABANDON"
    assert data["status"] == "not_evaluable_missing_plumbing"


# --- Bug B regression tests: build_signal_posts emits honest signal posts ---

def _ohlcv_df(prices, ticker="T1", seed=42):
    """Build a long-form OHLCV frame from a close-price path."""
    n = len(prices)
    dates = pd.date_range(end="2023-12-31", periods=n, freq="B")
    rng = np.random.default_rng(seed)
    o = np.array(prices) * (1 + rng.normal(0, 0.001, n))
    h = np.maximum(o, np.array(prices)) * (1 + rng.normal(0, 0.001, n))
    lo = np.minimum(o, np.array(prices)) * (1 - rng.normal(0, 0.001, n))
    v = np.full(n, 1_000_000)
    return pd.DataFrame({
        "Ticker": ticker, "Date": dates, "Open": o, "High": h,
        "Low": lo, "Close": prices, "Volume": v,
    })

def test_build_signal_posts_ta_rules_ema_cross_only_on_cross_days():
    from scripts.evaluate_candidate import build_signal_posts
    # Flat, dip, then recovery: exactly one EMA(10/50) cross-up above SMA(200).
    n = 260
    prices = np.full(n, 100.0)
    prices[200:210] = 95.0          # dip
    prices[210:220] = np.linspace(95, 105, 10)
    prices[220:] = 105.0            # recovery above SMA200
    df = _ohlcv_df(prices)
    spec = {
        "id": "t", "family": "ta_rules", "universe": "panel",
        "signal": {"entry": "ema_cross"},
        "parameters": {"ema_fast": 10, "ema_slow": 50, "sma_window": 200},
    }
    posts = build_signal_posts(spec, df, ["T1"])
    assert not posts.empty
    # Honest: posts are far fewer than total trading days.
    assert len(posts) < 50
    assert set(posts["ticker"]) == {"T1"}
    # Every post date must be a real cross-up day (EMA10>EMA50, prev cross, close>SMA200).
    t_df = df.set_index("Date").sort_index()
    fast = t_df["Close"].ewm(span=10, adjust=False).mean()
    slow = t_df["Close"].ewm(span=50, adjust=False).mean()
    sma200 = t_df["Close"].rolling(200).mean()
    cross = (fast.shift(1) <= slow.shift(1)) & (fast > slow) & (t_df["Close"] > sma200)
    for d in posts["post_date"]:
        assert cross.loc[d], f"post date {d} is not a cross-up day"

def test_build_signal_posts_ta_rules_rsi2_only_when_oversold():
    from scripts.evaluate_candidate import build_signal_posts, _rsi2_series
    n = 260
    prices = np.full(n, 100.0) + np.linspace(0, 30, n)
    prices[150:155] = [100.0, 90.0, 82.0, 78.0, 80.0]  # sharp 2-day drawdown -> RSI2 < 10
    df = _ohlcv_df(prices, seed=7)
    spec = {
        "id": "t", "family": "ta_rules", "universe": "panel",
        "signal": {"entry": "rsi2"},
        "parameters": {"entry": 10},
    }
    posts = build_signal_posts(spec, df, ["T1"])
    assert not posts.empty
    t_df = df.set_index("Date").sort_index()
    rsi2 = _rsi2_series(t_df["Close"])
    for d in posts["post_date"]:
        assert rsi2.loc[d] < 10, f"post date {d} has RSI2 {rsi2.loc[d]:.2f} >= 10"

def test_build_signal_posts_sentiment_sma_entry_only_above_sma():
    from scripts.evaluate_candidate import build_signal_posts
    n = 260
    prices = 100 * np.exp(np.linspace(-0.2, 0.4, n))  # crosses above SMA(200) partway
    df = _ohlcv_df(prices, ticker="SPY")
    spec = {
        "id": "t", "family": "sentiment_overlay", "universe": "SPY",
        "signal": {"entry": "sma_entry"},
        "parameters": {"window": 200},
    }
    posts = build_signal_posts(spec, df, ["SPY"])
    assert not posts.empty
    t_df = df.set_index("Date").sort_index()
    sma = t_df["Close"].rolling(200).mean()
    for d in posts["post_date"]:
        assert t_df["Close"].loc[d] > sma.loc[d], f"post date {d} not above SMA200"

def test_build_signal_posts_momentum_posts_only_on_month_end():
    from scripts.evaluate_candidate import build_signal_posts
    n = 400
    dates = pd.date_range(end="2023-12-31", periods=n, freq="B")
    up = 100 * np.exp(np.linspace(0, 0.5, n))     # winner
    down = 100 * np.exp(np.linspace(0, -0.5, n))  # loser
    frames = []
    for t, px in [("WIN", up), ("LOS", down)]:
        frames.append(_ohlcv_df(px, ticker=t))
    df = pd.concat(frames, ignore_index=True)
    spec = {
        "id": "t", "family": "sentiment_overlay", "universe": "panel",
        "signal": {"entry": "momentum_veto"},
        "parameters": {"top_n": 1, "lookback_days": 126, "skip_days": 21},
    }
    posts = build_signal_posts(spec, df, ["WIN", "LOS"])
    assert not posts.empty
    assert set(posts["ticker"]) == {"WIN"}  # only the momentum winner
    me = pd.Series(dates, index=dates)
    month_ends = set(me.groupby([me.dt.year, me.dt.month]).max())
    for d in posts["post_date"]:
        assert d in month_ends, f"post date {d} is not a month-end"

def test_entry_rule_normalizes_prose_specs():
    from scripts.evaluate_candidate import _entry_rule

    cases = [
        ({"signal": {"entry": "Buy when RSI(2) < 10 (short-term oversold)"},
          "indicators": [{"rsi2": "2-period RSI of close (Wilder)"}]}, "rsi2"),
        ({"signal": {"entry": "Buy when EMA(10) crosses above EMA(50) AND Close > SMA(200)"},
          "indicators": [{"ema10": "10-day EMA"}, {"ema50": "50-day EMA"}]}, "ema_cross"),
        ({"signal": {"entry": "Buy when MACD Histogram > 0 and increasing for 2 consecutive days"},
          "indicators": [{"macd_hist": "MACD Histogram"}]}, "macd_histogram"),
        ({"signal": {"entry": "on each month-end: pick the top 5 by 6m momentum (skip 1m)"}},
         "momentum"),
        ({"signal": {"entry": "enter all-in SPY when SPY close > SMA(200) AND sentiment score > 0.0"}},
         "sma_entry"),
        ({"signal": {"entry": "buy SPY when RSI(2) < 10"}}, "rsi2"),
        ({"signal": {"entry": "machine_key"}, "indicators": []}, "machine_key"),
    ]
    for spec, expected in cases:
        assert _entry_rule(spec) == expected, spec


def test_clamp_to_cache_uses_cached_coverage():
    from scripts.evaluate_candidate import _clamp_to_cache, _cached_coverage

    class FakeConn:
        def execute(self, _q):
            class FakeRes:
                def df(self):
                    return pd.DataFrame({"m": [pd.Timestamp("2024-06-11")],
                                         "x": [pd.Timestamp("2026-08-19 13:30:00")]})
            return FakeRes()

    class FakeCache:
        conn = FakeConn()

    class FakeProvider:
        cache = FakeCache()

    prov = FakeProvider()
    start = pd.Timestamp("2023-11-24")
    end = pd.Timestamp("2026-08-20")
    cs, ce = _clamp_to_cache(start, end, prov)
    assert cs == pd.Timestamp("2024-06-11")
    assert ce == pd.Timestamp("2026-08-19 13:30:00")
    assert _cached_coverage(prov) == (pd.Timestamp("2024-06-11"),
                                      pd.Timestamp("2026-08-19 13:30:00"))


def test_clamp_to_cache_noop_when_cache_empty():
    from scripts.evaluate_candidate import _clamp_to_cache

    class FakeConn:
        def execute(self, _q):
            class FakeRes:
                def df(self):
                    return pd.DataFrame({"m": [None], "x": [None]})
            return FakeRes()

    class FakeCache:
        conn = FakeConn()

    class FakeProvider:
        cache = FakeCache()

    start = pd.Timestamp("2023-11-24")
    end = pd.Timestamp("2026-08-20")
    cs, ce = _clamp_to_cache(start, end, FakeProvider())
    assert cs == start and ce == end


def test_main_permutations_and_signal_post_count():
    from scripts.evaluate_candidate import main
    import sys
    import tempfile
    import os
    import yaml

    with tempfile.TemporaryDirectory() as td:
        spec_path = os.path.join(td, "spec.yaml")
        eval_path = os.path.join(td, "eval.json")
        prereg_path = os.path.join(td, "prereg.md")
        spec = {
            "id": "t_perm", "name": "Test Perm", "family": "ta_rules", "universe": "panel",
            "signal": {"entry": "rsi2"},
            "parameters": {"entry": 10},
            "pre_registration_ref": prereg_path,
            "eval_records": eval_path,
        }
        with open(spec_path, "w") as f:
            yaml.dump(spec, f)

        n = 260
        prices = np.full(n, 100.0) + np.linspace(0, 30, n)
        prices[150:155] = [100.0, 90.0, 82.0, 78.0, 80.0]
        df = _ohlcv_df(prices)

        mock_provider = MagicMock()
        mock_provider.fetch_ohlcv.return_value = df
        with patch("scripts.evaluate_candidate.get_provider", return_value=mock_provider), \
             patch("scripts.evaluate_candidate.run_in_sample_test",
                   return_value=(0.1, 1.5, [0.1], [1.5], 0.04, None, None)), \
             patch("scripts.evaluate_candidate.run_walk_forward_test",
                   return_value=(0.1, 1.5, [0.1], [1.5], 0.03, 0.6, 10)):
            test_args = ["evaluate_candidate.py", spec_path, "--tickers", "T1",
                         "--days", "100", "--permutations", "40"]
            with patch.object(sys, 'argv', test_args):
                main()

        with open(eval_path, "r") as f:
            data = json.load(f)
        assert data["status"] == "evaluated"
        assert data["permutations_used"] == 40
        assert data["signal_post_count"] > 0
        assert data["signal_post_count"] < 100  # honest: not every trading day

def test_resolve_edge_claim_priority_and_fallback():
    from scripts.evaluate_candidate import _resolve_edge_claim
    spec_with_claim = {"family": "ta_rules", "edge_hypothesis": "Custom claim wins"}
    assert _resolve_edge_claim(spec_with_claim) == "Custom claim wins"
    # Unknown family (no brief file) falls back to Default claim.
    assert _resolve_edge_claim({"family": "no_such_family"}) == "Default claim"
    # Empty spec also falls back.
    assert _resolve_edge_claim({}) == "Default claim"
