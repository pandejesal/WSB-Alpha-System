import argparse
import json
import logging
import os
import re
import sys
import hashlib
import numpy as np
import pandas as pd
from datetime import datetime

from src.ops.strategy_registry import validate_spec
from src.ops.signals import generate_signals_from_registry, UnsupportedRuleShape
from src.data.providers.chain import get_provider
from src.backtest.validation import run_in_sample_test, run_walk_forward_test, NUM_PERMUTATIONS
from src.alpha.indicators import compute_indicators

logger = logging.getLogger(__name__)

# Benchmark/ETF names excluded from panel-style candidate universes (hunt briefs
# declare "liquid large-cap panel (excluding SPY/QQQ/AGG/BND)"). SPY-only specs
# (sentiment sma_entry, xgboost rsi2) evaluate on SPY alone.
_BENCHMARK_TICKERS = {"SPY", "QQQ", "AGG", "BND", "IWM"}

def _entry_rule(spec_dict):
    """Normalize a candidate's entry rule into a canonical machine key.

    Specs carry prose in signal.entry (e.g. 'Buy when RSI(2) < 10 ...') and
    machine keys in the indicators block. Normalization strips punctuation so
    both resolve to one of: rsi2 | macd_histogram | ema_cross | momentum |
    sma_entry. Falls back to the raw entry string when nothing matches.
    """
    entry = str(spec_dict.get("signal", {}).get("entry", ""))
    inds = spec_dict.get("indicators") or []
    keys = []
    for item in inds:
        if isinstance(item, dict):
            keys.extend(str(k) for k in item)
        else:
            keys.append(str(item))
    text = " ".join([entry] + keys).lower()
    n = re.sub(r"[^a-z0-9]", "", text)
    if "rsi2" in n:
        return "rsi2"
    if "macdhist" in n:
        return "macd_histogram"
    if "emacross" in n or "crossesabove" in n:
        return "ema_cross"
    if "momentum" in n or "monthend" in n:
        return "momentum"
    if "sma200" in n or "smaentry" in n:
        return "sma_entry"
    return entry

def compute_dsr(real_sharpe, permuted_sharpes):
    """
    Computes Deflated Sharpe Ratio (DSR) based on the conservative formula.
    DSR = Phi( (SR*sqrt(n-1) - skew*0.5*something) / sqrt(1-skew*SR + (kurt-1)/4*SR^2) )
    Here we implement a standard empirical p-value from permutation test as a proxy if we lack higher moments.
    Alternatively, a simple empirical DSR can be computed using standard normal CDF over the z-score of the sharpe
    vs the permuted sharpe distribution.
    """
    from scipy.stats import norm

    if len(permuted_sharpes) < 2:
        return 0.0

    SR = real_sharpe
    # Actually, DSR standard formula requires variance of the SRs
    sr_mean = np.mean(permuted_sharpes)
    sr_std = np.std(permuted_sharpes)
    if sr_std == 0:
        return 0.0

    # We use a basic empirical z-score approach to DSR
    z = (SR - sr_mean) / sr_std
    return norm.cdf(z)

def _get_universe(tickers_arg):
    if tickers_arg:
        return tickers_arg.split(",")
    try:
        with open("config/universe.json", "r") as f:
            univ = json.load(f)
            return univ.get("tickers", ["SPY"])
    except FileNotFoundError:
        return ["SPY"]

def _resolve_edge_claim(spec_dict):
    """Edge claim for the pre-registration doc.

    Priority: spec.edge_hypothesis -> hunts/<family>/brief.yaml hypothesis
    -> "Default claim". The brief dir uses dashes (multi-factor) while the
    family id uses underscores (multi_factor).
    """
    claim = spec_dict.get("edge_hypothesis")
    if claim:
        return claim
    family = spec_dict.get("family", "")
    if family:
        brief_dir = family.replace("_", "-")
        brief_path = os.path.join("hunts", brief_dir, "brief.yaml")
        try:
            if os.path.exists(brief_path):
                import yaml
                with open(brief_path, "r") as f:
                    brief = yaml.safe_load(f)
                hyp = (brief or {}).get("hypothesis")
                if hyp:
                    return str(hyp)
        except Exception as e:  # noqa: BLE001 - brief is best-effort metadata
            logger.warning(f"Could not read brief hypothesis from {brief_path}: {e}")
    return "Default claim"

def _universe_for_spec(spec_dict, tickers):
    """Restrict the evaluation universe to what the candidate spec declares.

    SPY-only specs (sentiment sma_entry, xgboost rsi2) evaluate on SPY alone;
    panel specs drop benchmark ETFs per the hunt briefs.
    """
    family = spec_dict.get("family", "")
    rule = _entry_rule(spec_dict)
    if (family == "sentiment_overlay" and rule == "sma_entry") or (
        family == "xgboost_exits" and rule == "rsi2"
    ):
        spy_only = [t for t in tickers if t == "SPY"]
        return spy_only or tickers[:1]
    return [t for t in tickers if t not in _BENCHMARK_TICKERS] or tickers

def _rsi2_series(close):
    """2-period RSI of close (Wilder-style ewm alpha=1/2), matching signals.py."""
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.ewm(alpha=1 / 2, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 2, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    return 100 - (100 / (1 + rs))

def _month_end_dates(index):
    s = pd.Series(index, index=index)
    return s.groupby([s.dt.year, s.dt.month]).max().tolist()

def _month_end_momentum_posts(df, universe, params):
    """Month-end top-N momentum posts (mirrors get_us_momentum_top5_signal).

    Emits one post per month-end for the top_n universe members by momentum
    (skip_days gap, lookback_days window). Aligns series on a common index.
    """
    lookback_days = int(params.get("lookback_days", 126))
    skip_days = int(params.get("skip_days", 21))
    top_n = int(params.get("top_n", 5))
    closes = {}
    for t in universe:
        t_df = df[df["Ticker"] == t].copy()
        if t_df.empty:
            continue
        closes[t] = t_df.set_index("Date").sort_index()["Close"].rename(t)
    if not closes:
        return []
    common = pd.concat(closes.values(), axis=1, join="outer").sort_index().ffill()
    posts = []
    for d in _month_end_dates(common.index):
        pos = common.index.get_loc(d)
        if pos < lookback_days + skip_days:
            continue
        p_skip = common.iloc[pos - skip_days]
        p_lookback = common.iloc[pos - (lookback_days + skip_days)]
        mom = (p_skip / p_lookback - 1).dropna()
        if mom.empty:
            continue
        top = mom.sort_values(ascending=False).head(top_n).index.tolist()
        for t in top:
            posts.append({"post_date": d, "ticker": t, "sentiment_score": 0.5})
    return posts

def build_signal_posts(spec_dict, df, tickers):
    """Generate honest signal posts for the validation engine.

    A post is emitted ONLY on the day the candidate's entry rule fires,
    mirroring the per-family entry logic in src/ops/signals.py. Posts carry
    sentiment_score=0.5 (neutral baseline, consistent with the signals layer) so the
    engine fills LONG at Open[t+1] with its standard hold. multi_factor is
    not evaluable here and raises UnsupportedRuleShape.
    """
    family = spec_dict.get("family", "")
    params = spec_dict.get("parameters") or {}
    rule = _entry_rule(spec_dict)
    universe = _universe_for_spec(spec_dict, tickers)
    posts = []

    def per_ticker_series():
        for t in universe:
            t_df = df[df["Ticker"] == t].copy()
            if t_df.empty:
                continue
            yield t, t_df.set_index("Date").sort_index()

    if family == "ta_rules":
        fast = params.get("ema_fast") or params.get("fast_ma", 20)
        slow = params.get("ema_slow") or params.get("slow_ma", 50)
        sma_window = int(params.get("sma_window", 200))
        consecutive = int(params.get("consecutive_days", 2))
        rsi_entry = params.get("entry", 10)
        for t, t_df in per_ticker_series():
            ind = compute_indicators(t_df)
            if ind is None or len(ind) < max(slow, sma_window) + 2:
                continue
            fast_col = f"EMA_{fast}"
            slow_col = f"EMA_{slow}"
            ind[fast_col] = t_df["Close"].ewm(span=fast, adjust=False).mean()
            ind[slow_col] = t_df["Close"].ewm(span=slow, adjust=False).mean()
            regime = t_df["Close"].rolling(sma_window).mean()
            if rule == "ema_cross":
                cross_up = (
                    (ind[fast_col].shift(1) <= ind[slow_col].shift(1))
                    & (ind[fast_col] > ind[slow_col])
                    & (t_df["Close"] > regime)
                )
                for d in ind.index[cross_up]:
                    posts.append({"post_date": d, "ticker": t, "sentiment_score": 0.5})
            elif rule == "macd_histogram":
                hist = ind["MACD_Hist"]
                rising = hist.diff() > 0
                for i in range(consecutive - 1, len(ind)):
                    window_rising = rising.iloc[i - consecutive + 1 : i + 1]
                    if hist.iloc[i] > 0 and bool(window_rising.all()):
                        posts.append({"post_date": ind.index[i], "ticker": t, "sentiment_score": 0.5})
            elif rule == "rsi2":
                rsi2 = _rsi2_series(t_df["Close"])
                for d in ind.index[rsi2 < rsi_entry]:
                    posts.append({"post_date": d, "ticker": t, "sentiment_score": 0.5})
    elif family == "sentiment_overlay":
        if rule == "sma_entry":
            window = int(params.get("window", 200))
            for t, t_df in per_ticker_series():
                above = t_df["Close"] > t_df["Close"].rolling(window).mean()
                for d in t_df.index[above]:
                    posts.append({"post_date": d, "ticker": t, "sentiment_score": 0.5})
        elif rule == "momentum":
            posts.extend(_month_end_momentum_posts(df, universe, params))
    elif family == "xgboost_exits":
        if rule == "rsi2":
            rsi_entry = params.get("entry", 10)
            for t, t_df in per_ticker_series():
                rsi2 = _rsi2_series(t_df["Close"])
                for d in t_df.index[rsi2 < rsi_entry]:
                    posts.append({"post_date": d, "ticker": t, "sentiment_score": 0.5})
        elif rule == "momentum":
            posts.extend(_month_end_momentum_posts(df, universe, params))
    else:
        raise UnsupportedRuleShape(
            f"NOT_EVALUABLE: no build_signal_posts support for family '{family}'"
        )

    return pd.DataFrame(posts, columns=["ticker", "post_date", "sentiment_score"])

def write_eval_record(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)

def print_summary(payload):
    print("\n" + "="*50)
    print("EVALUATION SUMMARY")
    print("="*50)
    print(f"Candidate : {payload.get('candidate_id')}")
    print(f"Family    : {payload.get('family')}")
    print(f"Verdict   : {payload.get('verdict')}")
    print(f"Status    : {payload.get('status')}")
    print("-"*50)
    print(f"IS P-Value: {payload.get('in_sample_p_value')}")
    print(f"WF P-Value: {payload.get('walk_forward_p_value')}")
    print(f"DSR       : {payload.get('dsr')}")
    print("="*50 + "\n")

def _cached_coverage(provider):
    """Return (min_date, max_date) of cached OHLCV rows, or None if cache is empty."""
    try:
        res = provider.cache.conn.execute(
            "SELECT MIN(date) AS m, MAX(date) AS x FROM ohlcv"
        ).df()
        if res.empty or pd.isna(res.iloc[0]['m']) or pd.isna(res.iloc[0]['x']):
            return None
        return pd.Timestamp(res.iloc[0]['m']), pd.Timestamp(res.iloc[0]['x'])
    except Exception:  # noqa: BLE001 - cache must never block evaluation
        return None

def _clamp_to_cache(start_date, end_date, provider):
    """Clamp the requested window to cached coverage so the chain serves
    from DuckDB instead of refetching (yfinance batch fails on NaN-volume rows)."""
    cov = _cached_coverage(provider)
    if cov is None:
        return start_date, end_date
    cache_min, cache_max = cov
    return max(start_date, cache_min), min(end_date, cache_max)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("spec_yaml", help="Path to the candidate spec.yaml")
    parser.add_argument("--tickers", help="Comma separated tickers (e.g. T1,T2)")
    parser.add_argument("--days", type=int, default=60, help="Days of data to fetch")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--permutations", type=int, default=NUM_PERMUTATIONS,
                        help="Number of permutation runs per test (default %(default)s)")

    args = parser.parse_args()

    np.random.seed(args.seed)

    if args.permutations != NUM_PERMUTATIONS:
        import src.backtest.validation as validation_mod
        validation_mod.NUM_PERMUTATIONS = args.permutations

    # 1. Load and validate spec
    try:
        with open(args.spec_yaml, 'r') as f:
            import yaml
            spec_dict = yaml.safe_load(f)
            if not isinstance(spec_dict, dict):
                raise ValueError("Spec must be a dictionary")
        validate_spec(spec_dict, filepath=args.spec_yaml)
    except Exception as e:
        logger.error(f"Spec validation failed: {e}")
        sys.exit(1)

    spec_id = spec_dict.get("id")
    family = spec_dict.get("family")

    # 2. Resolve paths
    prereg_ref = spec_dict.get("pre_registration_ref")
    eval_ref = spec_dict.get("eval_records")

    if not prereg_ref or not eval_ref:
        logger.error("Spec missing pre_registration_ref or eval_records")
        sys.exit(1)

    # 3. Pre-registration doc generation
    if not os.path.exists(prereg_ref):
        logger.info(f"Generating missing preregistration doc at {prereg_ref}")
        try:
            # We bypass the cycle extraction and directly use the filename logic
            # to match the exact path in spec
            os.makedirs(os.path.dirname(prereg_ref), exist_ok=True)
            with open(args.spec_yaml, 'r') as f:
                spec_content = f.read()
            claim = _resolve_edge_claim(spec_dict)
            doc_content = f"## Claim\n{claim}\n\n## Strategy Spec\n```yaml\n{spec_content}\n```\n"
            with open(prereg_ref, 'w') as f:
                f.write(doc_content)
        except Exception as e:
            logger.error(f"Failed to write prereg doc: {e}")

    with open(args.spec_yaml, 'r') as f:
        spec_content = f.read()
    spec_fingerprint = hashlib.sha256(spec_content.encode('utf-8')).hexdigest()

    # 4 & 5. Evaluation and Signal Generation
    try:
        # Check for families that need plumbing this harness cannot run.
        # multi_factor: factor modules missing. xgboost_exits: the exit
        # classifier requires a 'target' column that compute_indicators()
        # does not carry (signals.py sets it on the raw df), so the signal
        # generation step raises before evaluation can be honest.
        if family in ("multi_factor", "xgboost_exits"):
            raise UnsupportedRuleShape("NOT_EVALUABLE: missing factor modules")

        tickers = _get_universe(args.tickers)

        provider = get_provider()
        end_date = datetime.now()
        start_date = end_date - pd.Timedelta(days=args.days * 2) # double days to account for weekends/holidays
        start_date, end_date = _clamp_to_cache(start_date, end_date, provider)
        df = provider.fetch_ohlcv(tickers, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))

        if df is None or df.empty:
             raise ValueError("Failed to fetch data")

        # Test signal generation
        entry = {"spec": spec_dict, "status": "active"}
        signals = generate_signals_from_registry(df, [entry], tickers)

        if spec_id not in signals or signals[spec_id].get("signal") == "FLAT":
             logger.warning("Strategy generated no signals or FLAT.")
             # We continue to backtest, it will just result in 0 returns.

        # Build honest signal posts for the validation engine: one post per day
        # the entry rule fires, per family (Bug B: no fabricated every-day posts).
        posts_df = build_signal_posts(spec_dict, df, tickers)

        if posts_df.empty:
            logger.warning("Strategy produced no signal posts; evaluation reflects zero trades.")

        stock_dfs = {}
        for t in tickers:
            t_df = df[df['Ticker'] == t].copy()
            if t_df.empty:
                continue
            t_df = t_df.set_index('Date').sort_index()
            ind = compute_indicators(t_df)
            if ind is not None and len(ind) >= 20:
                stock_dfs[t] = ind
        spy_close = stock_dfs[tickers[0]]['Close'] if stock_dfs else pd.Series(dtype=float)

        # Wrap in list so it meets what validation expects if needed
        real_ret, real_sharpe, permuted_rets, permuted_sharpes, in_sample_p_value, _, _ = run_in_sample_test(posts_df, stock_dfs, spy_close)

        real_pooled_ret, real_pooled_sharpe, pooled_permuted_rets, pooled_permuted_sharpes, walk_forward_p_value, walk_forward_win_rate, num_windows = run_walk_forward_test(posts_df, stock_dfs, spy_close)

        dsr = compute_dsr(real_sharpe, permuted_sharpes)

        payload = {
            "candidate_id": spec_id,
            "family": family,
            "verdict": "PASS" if in_sample_p_value < 0.05 and walk_forward_p_value < 0.05 else "FAIL",
            "status": "evaluated",
            "in_sample_p_value": in_sample_p_value,
            "walk_forward_p_value": walk_forward_p_value,
            "walk_forward_win_rate": walk_forward_win_rate,
            "num_windows": num_windows,
            "real_sharpe": real_sharpe,
            "real_return": real_ret,
            "oos_sharpe": real_pooled_sharpe,
            "dsr": dsr,
            "permutations_used": args.permutations,
            "signal_post_count": int(len(posts_df)),
            "edge_gate_params": spec_dict.get("edge_gate_params", {}),
            "spec_fingerprint": spec_fingerprint,
            "timestamp": datetime.utcnow().isoformat()
        }

    except UnsupportedRuleShape as e:
        if "missing factor modules" in str(e):
             print(f"NOT_EVALUABLE: {e}")
             payload = {
                 "candidate_id": spec_id,
                 "family": family,
                 "verdict": "HONEST_ABANDON",
                 "status": "not_evaluable_missing_plumbing",
                 "spec_fingerprint": spec_fingerprint,
                 "timestamp": datetime.utcnow().isoformat()
             }
        else:
             raise

    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        payload = {
            "candidate_id": spec_id,
            "family": family,
            "verdict": "FAIL",
            "status": f"error: {str(e)}",
            "spec_fingerprint": spec_fingerprint,
            "timestamp": datetime.utcnow().isoformat()
        }

    # 6. Write Eval JSON and print summary
    write_eval_record(eval_ref, payload)
    print_summary(payload)

    if payload.get("verdict") == "HONEST_ABANDON":
        sys.exit(0)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
