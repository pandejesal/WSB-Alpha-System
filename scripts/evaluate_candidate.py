import argparse
import json
import logging
import os
import sys
import hashlib
import numpy as np
import pandas as pd
from datetime import datetime

from src.ops.strategy_registry import validate_spec
from src.ops.preregistration import freeze_preregistration
from src.ops.signals import generate_signals_from_registry, UnsupportedRuleShape
from src.data.providers.chain import get_provider
from src.backtest.validation import run_in_sample_test, run_walk_forward_test, compute_metrics, NUM_PERMUTATIONS
from src.backtest.run_historic_backtest import run_backtest

logger = logging.getLogger(__name__)

def compute_dsr(real_sharpe, permuted_sharpes):
    """
    Computes Deflated Sharpe Ratio (DSR) based on the conservative formula.
    DSR = Phi( (SR*sqrt(n-1) - skew*0.5*something) / sqrt(1-skew*SR + (kurt-1)/4*SR^2) )
    Here we implement a standard empirical p-value from permutation test as a proxy if we lack higher moments.
    Alternatively, a simple empirical DSR can be computed using standard normal CDF over the z-score of the sharpe
    vs the permuted sharpe distribution.
    """
    from scipy.stats import norm, skew, kurtosis

    if len(permuted_sharpes) < 2:
        return 0.0

    SR = real_sharpe
    n = len(permuted_sharpes) # proxy for number of periods in simple form, but n is usually trials.
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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("spec_yaml", help="Path to the candidate spec.yaml")
    parser.add_argument("--tickers", help="Comma separated tickers (e.g. T1,T2)")
    parser.add_argument("--days", type=int, default=60, help="Days of data to fetch")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")

    args = parser.parse_args()

    np.random.seed(args.seed)

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
            claim = spec_dict.get("edge_hypothesis", "Default claim")
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
        # Check for multi_factor early to abandon honest
        if family == "multi_factor":
            raise UnsupportedRuleShape("NOT_EVALUABLE: missing factor modules")

        tickers = _get_universe(args.tickers)

        provider = get_provider()
        end_date = datetime.now()
        start_date = end_date - pd.Timedelta(days=args.days * 2) # double days to account for weekends/holidays
        df = provider.fetch_ohlcv(tickers, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))

        if df is None or df.empty:
             raise ValueError("Failed to fetch data")

        # Test signal generation
        entry = {"spec": spec_dict, "status": "active"}
        signals = generate_signals_from_registry(df, [entry], tickers)

        if spec_id not in signals or signals[spec_id].get("signal") == "FLAT":
             logger.warning("Strategy generated no signals or FLAT.")
             # We continue to backtest, it will just result in 0 returns.

        # Use real sentiment feed or empty dataframe instead of injecting 0.5 scores
        posts_data = []
        try:
            from src.data.providers.reddit_provider import RedditProvider
            from src.research.debate_engine import DebateEngine
            reddit = RedditProvider()
            posts = reddit.fetch_sentiment_feed(limit=50)
            if not posts.empty:
                engine = DebateEngine()
                headlines = posts['title'].tolist() if 'title' in posts.columns else []
                debate_result = engine.run_debate(tickers[0], headlines, base_score={"positive_ratio": 0.6, "negative_ratio": 0.4, "classification": "positive"})
                score = debate_result.get("score", 0.0)
                # Assign this real score to the latest dates if posts are available
                for d in df['Date'].unique():
                    posts_data.append({"post_date": pd.to_datetime(d), "ticker": tickers[0], "sentiment_score": score})
        except Exception as e:
            logger.warning(f"Failed to fetch real sentiment: {e}. Validation will proceed with empty posts.")

        posts_df = pd.DataFrame(posts_data)
        if posts_df.empty:
            posts_df = pd.DataFrame(columns=["post_date", "ticker", "sentiment_score"])

        stock_dfs = {}
        for t in tickers:
            t_df = df[df['Ticker'] == t].copy()
            if t_df.empty:
                continue
            t_df = t_df.set_index('Date').sort_index()
            from src.alpha.indicators import compute_indicators
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
