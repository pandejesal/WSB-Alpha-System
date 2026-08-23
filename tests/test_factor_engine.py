"""Phase 3 (Cycle 2): factor engine correctness tests.

- Hand-computed monthly closes / MOM12-1 / REV1 / composite-decile membership.
- Engine reproduces a hand-computed 4-week long-short return example.
- No-lookahead: mutating signal-day or post-signal bars must not change
  that week's positions (factor inputs are strictly before the signal bar).
"""
import numpy as np
import pandas as pd
import pytest

from scripts.factor_engine import (
    factor_panel, monthly_last_close, rank_week, run_engine,
    union_calendar, weekly_signal_dates, null_distribution,
    time_shuffle_null,
)


def make_frames(n_tickers=20, n_months=21, seed=42):
    """Deterministic synthetic OHLCV: 2019-01 .. 2019-01 + n_months."""
    rng = np.random.RandomState(seed)
    start = pd.Timestamp("2019-01-01")
    end = start + pd.DateOffset(months=n_months) - pd.Timedelta(days=1)
    dates = pd.bdate_range(start, end)
    frames = {}
    for t in range(n_tickers):
        idx = np.arange(len(dates))
        base = 10.0 + t * 1.7
        drift = 0.15 + 0.02 * t
        close = base * (1 + drift * idx / 250.0) * (
            1 + 0.02 * np.sin(2 * np.pi * idx / 40.0 + t / 2.0))
        close = np.round(close, 2)
        open_ = np.concatenate([[close[0]], close[:-1]])
        high = np.maximum(open_, close) * 1.005
        low = np.minimum(open_, close) * 0.995
        vol = np.round(rng.randint(1e5, 5e5, size=len(dates)))
        frames[f"T{t:02d}"] = pd.DataFrame(
            {"open": open_, "high": high, "low": low, "close": close,
             "volume": vol}, index=dates)
    return frames


# ---------------------------------------------------------------- hand checks

def test_monthly_last_close_hand():
    frames = make_frames(n_tickers=2, n_months=4, seed=1)
    mc = monthly_last_close(frames)
    for t, df in frames.items():
        expect = df["close"].groupby(df.index.to_period("M")).last()
        pd.testing.assert_series_equal(mc[t], expect)


def test_factors_hand():
    frames = make_frames(n_tickers=2, n_months=16, seed=2)
    mc = monthly_last_close(frames)
    p = factor_panel(mc)
    t = "T01"
    s = mc[t]
    mom = s.shift(2) / s.shift(12) - 1.0
    rev = s.shift(1) / s.shift(2) - 1.0
    pd.testing.assert_series_equal(p[t]["mom12_1"], mom,
                                   check_names=False)
    pd.testing.assert_series_equal(p[t]["rev1"], rev, check_names=False)
    m = pd.Period("2020-01", freq="M")
    assert np.isclose(p[t].loc[m, "mom12_1"],
                      s.loc[m - 2] / s.loc[m - 12] - 1.0)
    assert np.isclose(p[t].loc[m, "rev1"], s.loc[m - 1] / s.loc[m - 2] - 1.0)


def test_rank_composite_hand():
    frames = make_frames(n_tickers=10, n_months=16, seed=3)
    mc = monthly_last_close(frames)
    p = factor_panel(mc)
    m = pd.Period("2020-02", freq="M")
    row = pd.DataFrame({t: p[t].loc[m] for t in sorted(frames)}).T
    row.columns = ["mom12_1", "rev1"]
    ranked = rank_week(row, sorted(frames))
    # independent hand calc
    rmom = row["mom12_1"].rank(method="average")
    rrev = row["rev1"].rank(method="average")
    n = len(row)
    comp = (rmom - 1) / (n - 1) + 1 - (rrev - 1) / (n - 1)
    pct = (comp.rank(method="average") - 1) / (n - 1)
    assert np.allclose(ranked["composite"].reindex(row.index).values,
                       comp.values)
    assert np.allclose(ranked["pct_comp"].reindex(row.index).values,
                       pct.values)


def test_4week_return_hand():
    """Engine reproduces a hand-computed 4-week long-short return example."""
    frames = make_frames(n_tickers=20, n_months=21, seed=42)
    mc = monthly_last_close(frames)
    p = factor_panel(mc)
    cal = union_calendar(frames)
    sched = weekly_signal_dates(cal)
    res = run_engine(frames, monthly=mc, panel=p, schedule=sched)
    valid = res["returns"].dropna(subset=["factor_return"]).reset_index(drop=True)

    # hand: first 4 factor weeks with defined factors
    tickers = sorted(frames)
    # hand rank helper (independent of engine)
    def hand_week(d):
        m = d.to_period("M")
        mom = {t: (mc[t].loc[m - 2] / mc[t].loc[m - 12] - 1.0) for t in tickers}
        rev = {t: (mc[t].loc[m - 1] / mc[t].loc[m - 2] - 1.0) for t in tickers}
        mdf = pd.DataFrame({"mom": mom, "rev": rev}).dropna()
        rmom = mdf["mom"].rank(method="average")
        rrev = mdf["rev"].rank(method="average")
        n = len(mdf)
        comp = (rmom - 1) / (n - 1) + 1 - (rrev - 1) / (n - 1)
        pct = (comp.rank(method="average") - 1) / (n - 1)
        return mdf.index[(pct >= 0.90).values], mdf.index[(pct <= 0.10).values]

    def hand_window(execs):
        e0, e1 = execs
        def ret(tlist):
            rs = []
            for t in tlist:
                o0 = frames[t]["open"].loc[e0]
                o1 = frames[t]["open"].loc[e1]
                rs.append(o1 / o0 - 1.0)
            return rs
        return (float(np.mean(ret(hand_week(valid.loc[i, "signal_date"])[0])))
                - float(np.mean(ret(hand_week(valid.loc[i, "signal_date"])[1]))))

    assert len(valid) >= 4
    for i in range(4):
        d = valid.loc[i, "signal_date"]
        e0 = valid.loc[i, "exec_date"]
        e1 = valid.loc[i + 1, "exec_date"]
        assert d.to_period("M") >= pd.Period("2020-01", freq="M")
        expect = hand_window((e0, e1))
        assert valid.loc[i, "factor_return"] == pytest.approx(expect, abs=1e-12)
        # position rows exist for this week with sane weights
        wk_rows = res["positions"][res["positions"]["week"] == valid.loc[i, "week"]]
        assert len(wk_rows) == 4  # 2 long + 2 short
        assert wk_rows[wk_rows["side"] == "L"]["weight"].sum() == pytest.approx(1.0)
        assert wk_rows[wk_rows["side"] == "S"]["weight"].sum() == pytest.approx(1.0)


# -------------------------------------------------------------- no-lookahead

def test_no_lookahead_mutations():
    frames = make_frames(n_tickers=20, n_months=18, seed=7)
    res = run_engine(frames)
    valid = res["returns"].dropna(subset=["factor_return"]).reset_index(drop=True)
    i = 0
    wk = valid.loc[i, "week"]
    d = valid.loc[i, "signal_date"]
    e = valid.loc[i, "exec_date"]
    base_pos = res["positions"][res["positions"]["week"] == wk]
    assert len(base_pos) == 4

    # mutate the signal-day close AND a post-signal close -> week-k positions
    # must be unchanged (factor inputs are strictly before the signal bar)
    mutated = {t: df.copy() for t, df in frames.items()}
    for t in mutated:
        mutated[t].loc[d, "close"] *= 1.5
        mutated[t].loc[e, "close"] *= 0.5
    res2 = run_engine(mutated)
    pos2 = res2["positions"][res2["positions"]["week"] == wk]
    pd.testing.assert_frame_equal(
        pos2.sort_values(["ticker", "side"]).reset_index(drop=True),
        base_pos.sort_values(["ticker", "side"]).reset_index(drop=True))

    # a bar BEFORE the signal date legitimately changes factors -> week-k
    # positions MAY change (sanity: engine still runs and returns rows)
    pre = frames["T01"].index[frames["T01"].index < d][-1]
    mutated2 = {t: df.copy() for t, df in frames.items()}
    mutated2["T01"].loc[pre, "close"] *= 0.4
    res3 = run_engine(mutated2)
    assert len(res3["positions"]) == len(res["positions"])


def test_positions_log_consistency():
    frames = make_frames(n_tickers=20, n_months=18, seed=9)
    res = run_engine(frames)
    pos = res["positions"]
    assert not pos.empty
    assert (pos["exec_date"] > pos["signal_date"]).all()
    for wk, grp in pos.groupby("week"):
        for side in ["L", "S"]:
            g = grp[grp["side"] == side]
            assert len(g) >= 1
            assert g["weight"].sum() == pytest.approx(1.0)
            assert (g["weight"] == g["weight"].iloc[0]).all()


def test_ls_components_present():
    frames = make_frames(n_tickers=20, n_months=18, seed=11)
    res = run_engine(frames)
    r = res["returns"]
    for col in ("factor_return", "mom_ls", "rev_ls"):
        assert col in r.columns
    valid = r.dropna(subset=["factor_return"])
    assert valid["mom_ls"].notna().mean() > 0.9
    assert valid["rev_ls"].notna().mean() > 0.9


def test_mom_rev_sign_sensitivity():
    """A frame engineered so past winners keep winning must show positive
    mom_ls and (mechanically) the reverse for rev_ls ordering sanity."""
    frames = make_frames(n_tickers=20, n_months=21, seed=13)
    # amplify momentum: multiply each ticker's prices by a growing trend factor
    for t, df in frames.items():
        k = int(t[1:]) + 1
        trend = 1.0 + 0.0015 * k * np.arange(len(df)) / 250.0
        for col in ("open", "high", "low", "close"):
            df[col] = df[col] * trend
    res = run_engine(frames)
    r = res["returns"].dropna(subset=["factor_return"])
    assert r["mom_ls"].mean() > 0


def test_nulls_run():
    frames = make_frames(n_tickers=20, n_months=18, seed=17)
    perm = null_distribution(frames, n=5, seed=0,
                             oos_start=pd.Timestamp("2020-01-01"))
    assert len(perm) == 5
    assert perm["median"].notna().all() and perm["sharpe_ann"].notna().all()
    ser = pd.Series(np.linspace(0.01, 0.10, 20))
    tsh = time_shuffle_null(ser, n=5, seed=0)
    assert len(tsh) == 5
    # median invariant under time permutation
    assert np.allclose(tsh["median"], ser.median())