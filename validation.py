import pandas as pd
import numpy as np
import logging
import yfinance as yf
from datetime import timedelta
from run_historic_backtest import compute_indicators, evaluate_strategy_on_data

# Configure logging
logging.basicConfig(filename='rejected_strategies.log', level=logging.INFO, format='%(asctime)s - %(message)s')

def run_permutation_test(n_permutations=200):
    print("Loading data...")
    posts_df = pd.read_csv("wsb_factual_research_data.csv")
    posts_df["post_date"] = pd.to_datetime(posts_df["post_date"])

    unique_tickers = posts_df["ticker"].unique().tolist()
    min_date = posts_df["post_date"].min() - timedelta(days=60)
    max_date = posts_df["post_date"].max() + timedelta(days=450)

    print("Downloading pricing data...")
    px_data = yf.download(unique_tickers + ["SPY"], start=min_date, end=max_date, progress=False, auto_adjust=True)

    spy = px_data.loc[:, (slice(None), "SPY")].copy()
    spy.columns = spy.columns.get_level_values(0)
    spy_close = spy["Close"].dropna()

    stock_dfs = {}
    for ticker in unique_tickers:
        t_px = px_data.loc[:, (slice(None), ticker)].copy()
        t_px.columns = t_px.columns.get_level_values(0)
        t_px = t_px.dropna(subset=["Close", "Open", "High", "Low"])
        if len(t_px) >= 20:
            stock_dfs[ticker] = compute_indicators(t_px)

    print("Evaluating real strategy (in-sample)...")
    real_return = evaluate_strategy_on_data(posts_df, stock_dfs, spy_close, return_type="total_return")
    print(f"Real In-Sample Return: {real_return * 100:.2f}%")

    print(f"Running In-Sample Permutation Test ({n_permutations} permutations)...")
    better_or_equal_count = 0
    for i in range(n_permutations):
        permuted_posts = posts_df.copy()
        # Permute sentiment dates
        permuted_posts["post_date"] = np.random.permutation(permuted_posts["post_date"])

        permuted_ret = evaluate_strategy_on_data(permuted_posts, stock_dfs, spy_close, return_type="total_return")
        if permuted_ret >= real_return:
            better_or_equal_count += 1

        if (i + 1) % 50 == 0:
            print(f"  Completed {i + 1} permutations...")

    in_sample_p_value = better_or_equal_count / n_permutations
    print(f"In-Sample p-value: {in_sample_p_value:.4f}")

    # --- Rolling Walk-Forward ---
    print("Running Rolling Walk-Forward Permutation Test...")

    # Sort posts by date for walk-forward
    posts_df = posts_df.sort_values(by="post_date").reset_index(drop=True)

    # Time limits
    start_date = posts_df["post_date"].min()
    end_date = posts_df["post_date"].max()

    # Holdout period (last 6 months)
    holdout_start = end_date - timedelta(days=180)

    # Walk-forward setup
    train_window = timedelta(days=3*365) # 3 years
    test_window = timedelta(days=90) # 90 days

    current_train_end = start_date + train_window

    wf_real_returns = []
    wf_permuted_returns = {i: [] for i in range(n_permutations)}

    fold_count = 0
    while current_train_end < holdout_start:
        test_start = current_train_end
        test_end = min(test_start + test_window, holdout_start)

        test_posts = posts_df[(posts_df["post_date"] >= test_start) & (posts_df["post_date"] < test_end)]

        if len(test_posts) > 0:
            real_fold_ret = evaluate_strategy_on_data(test_posts, stock_dfs, spy_close, return_type="total_return")
            wf_real_returns.append(real_fold_ret)

            for i in range(n_permutations):
                permuted_test_posts = test_posts.copy()
                permuted_test_posts["post_date"] = np.random.permutation(permuted_test_posts["post_date"])
                perm_fold_ret = evaluate_strategy_on_data(permuted_test_posts, stock_dfs, spy_close, return_type="total_return")
                wf_permuted_returns[i].append(perm_fold_ret)

        current_train_end += test_window
        fold_count += 1

    real_wf_total_return = sum(wf_real_returns)
    wf_better_or_equal = 0
    for i in range(n_permutations):
        perm_wf_total = sum(wf_permuted_returns[i])
        if perm_wf_total >= real_wf_total_return:
            wf_better_or_equal += 1

    wf_p_value = wf_better_or_equal / n_permutations
    print(f"Walk-Forward p-value (Multi-year, {fold_count} folds): {wf_p_value:.4f}")

    # Enforce rules
    failed = False
    reasons = []
    if in_sample_p_value > 0.01:
        failed = True
        reasons.append(f"In-sample p-value > 1% ({in_sample_p_value:.4f})")
    if wf_p_value > 0.01: # Multi-year
        failed = True
        reasons.append(f"Walk-forward p-value > 1% ({wf_p_value:.4f})")

    if failed:
        reason_str = " | ".join(reasons)
        logging.info(f"Strategy Alpha Fusion Rejected: {reason_str}")
        print(f"\nVALIDATION FAILED: {reason_str}")
        return False
    else:
        print("\nVALIDATION PASSED!")
        return True

if __name__ == "__main__":
    run_permutation_test()
