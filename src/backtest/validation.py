import pandas as pd
import numpy as np
import yfinance as yf
from datetime import timedelta
import matplotlib.pyplot as plt
from src.alpha import indicators
import src.backtest.run_historic_backtest as rb
from tqdm import tqdm

NUM_PERMUTATIONS = 200

def load_base_data():
    import os
    csv_path = "wsb_factual_research_data.csv"

    if not os.path.exists(csv_path):
        print("No sentiment data found. Using technical-only universe.")
        import json
        with open("config/universe.json") as f:
            universe = json.load(f).get("tickers", [])

        # Create synthetic signals from technical indicators
        print("Downloading baseline pricing data for synthetic signals...")
        px_data = yf.download(universe, period="2y", progress=False, auto_adjust=True)
        synthetic_signals = []
        for ticker in universe:
            try:
                t_px = px_data.loc[:, (slice(None), ticker)].copy()
                t_px.columns = t_px.columns.get_level_values(0)
                t_px = t_px.dropna(subset=["Close", "Open", "High", "Low"])
                if len(t_px) < 50:
                    continue
                ind_df = indicators.compute_indicators(t_px)

                # Generate synthetic signals for backtesting
                for idx, row in ind_df.iterrows():
                    rsi = row.get('RSI_14', 50)
                    macd_hist = row.get('MACD_Hist', 0)
                    close = row['Close']
                    bb_lower = row.get('BB_Lower', close * 0.95)
                    bb_upper = row.get('BB_Upper', close * 1.05)
                    ha_close = row.get('HA_Close', close)
                    ha_open = row.get('HA_Open', close)
                    gk_vol = row.get('GK_Vol', 0.50)
                    ema_20 = row.get('EMA_20', close)

                    volatility_shield_passed = gk_vol < 1.20
                    bullish_score = int(ha_close > ha_open) + int((close > ema_20) and (macd_hist > 0)) + int(30 < rsi < 70) + int(close > bb_lower)
                    bearish_score = int(ha_close < ha_open) + int((close < ema_20) and (macd_hist < 0)) + int(30 < rsi < 70) + int(close < bb_upper)

                    if volatility_shield_passed:
                        if bullish_score >= 3:
                            synthetic_signals.append({"ticker": ticker, "post_date": idx, "sentiment_score": 1.0})
                        elif bearish_score >= 3:
                            synthetic_signals.append({"ticker": ticker, "post_date": idx, "sentiment_score": -1.0})
            except:
                continue
        posts_df = pd.DataFrame(synthetic_signals)
    else:
        posts_df = pd.read_csv(csv_path)
        posts_df["post_date"] = pd.to_datetime(posts_df["post_date"])

    unique_tickers = posts_df["ticker"].unique().tolist()
    min_date = posts_df["post_date"].min() - timedelta(days=60)
    max_date = posts_df["post_date"].max() + timedelta(days=450)

    print("Downloading baseline pricing data for permutations...")
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
            stock_dfs[ticker] = indicators.compute_indicators(t_px)

    return posts_df, stock_dfs, spy_close

def compute_metrics(trades_df):
    if len(trades_df) == 0:
        return 0.0, 0.0
    # Sorting by post_date to compute accurate cumsum total returns
    trades_sorted = trades_df.sort_values(by="post_date").reset_index(drop=True)
    tot_return = trades_sorted["return"].fillna(0).sum()

    rets = trades_sorted["return"].fillna(0)
    std = rets.std()
    sharpe = (rets.mean() / (std + 1e-10)) * np.sqrt(100) if std > 0 else 0.0
    return tot_return, sharpe

def run_in_sample_test(posts_df, stock_dfs, spy_close):
    print(f"\n--- Running In-Sample Permutation Test ({NUM_PERMUTATIONS} runs) ---")

    # Real run
    real_trades = rb.run_backtest(custom_posts_df=posts_df, stock_dfs_preloaded=stock_dfs, spy_close_preloaded=spy_close)
    real_ret, real_sharpe = compute_metrics(real_trades)
    print(f"Real In-Sample -> Return: {real_ret*100:.2f}%, Sharpe: {real_sharpe:.2f}")

    permuted_rets = []
    permuted_sharpes = []

    # Identify eligible dates per ticker
    eligible_dates_per_ticker = {}
    for ticker, df in stock_dfs.items():
        eligible_dates_per_ticker[ticker] = df.index.tolist()

    for i in tqdm(range(NUM_PERMUTATIONS), desc="In-Sample Permutations"):
        shuffled_posts = posts_df.copy()

        # Shuffle within each ticker
        for ticker in shuffled_posts["ticker"].unique():
            if ticker not in eligible_dates_per_ticker:
                continue
            mask = shuffled_posts["ticker"] == ticker
            n_signals = mask.sum()
            # Randomly pick n_signals dates from the available dates for this ticker
            chosen_dates = np.random.choice(eligible_dates_per_ticker[ticker], size=n_signals, replace=True)
            shuffled_posts.loc[mask, "post_date"] = chosen_dates

        shuffled_trades = rb.run_backtest(custom_posts_df=shuffled_posts, stock_dfs_preloaded=stock_dfs, spy_close_preloaded=spy_close)
        p_ret, p_sharpe = compute_metrics(shuffled_trades)
        permuted_rets.append(p_ret)
        permuted_sharpes.append(p_sharpe)

    permuted_rets = np.array(permuted_rets)
    permuted_sharpes = np.array(permuted_sharpes)

    # P-value: fraction of permutations matching or beating real on BOTH return and sharpe
    beat_both = np.sum((permuted_rets >= real_ret) & (permuted_sharpes >= real_sharpe))
    p_value = beat_both / NUM_PERMUTATIONS
    print(f"In-Sample P-Value: {p_value:.4f}")

    return real_ret, real_sharpe, permuted_rets, permuted_sharpes, p_value


def run_walk_forward_test(posts_df, stock_dfs, spy_close):
    print(f"\n--- Running Walk-Forward Permutation Test ({NUM_PERMUTATIONS} runs) ---")

    start_date = posts_df["post_date"].min()
    end_date = posts_df["post_date"].max()

    # 90-day windows rolling forward
    windows = []
    current_start = start_date
    while current_start < end_date:
        window_end = current_start + timedelta(days=90)
        windows.append((current_start, window_end))
        current_start = window_end

    print(f"Total rolling 90-day windows: {len(windows)}")

    # We will pool out-of-sample trades across all windows.
    # Actually, in a true walk-forward where no parameters are fitted, the out-of-sample is just the whole dataset
    # evaluated in 90-day chunks.
    # As instructed: "compute pooled performance across all rolling windows for both real and permuted...
    # but also report what fraction of individual windows show real beating the permuted median."

    # First, let's get real trades for each window
    real_trades = rb.run_backtest(custom_posts_df=posts_df, stock_dfs_preloaded=stock_dfs, spy_close_preloaded=spy_close)

    real_window_rets = []
    real_window_sharpes = []
    for w_start, w_end in windows:
        w_trades = real_trades[(real_trades["post_date"] >= w_start) & (real_trades["post_date"] < w_end)]
        r, s = compute_metrics(w_trades)
        real_window_rets.append(r)
        real_window_sharpes.append(s)

    real_pooled_ret, real_pooled_sharpe = compute_metrics(real_trades)

    pooled_permuted_rets = []
    pooled_permuted_sharpes = []

    # To keep track of permutations per window
    window_permuted_rets = {i: [] for i in range(len(windows))}

    # To do this efficiently, we can shuffle dates within each window.
    for p in tqdm(range(NUM_PERMUTATIONS), desc="Walk-Forward Permutations"):
        shuffled_posts = posts_df.copy()

        for w_start, w_end in windows:
            w_mask = (shuffled_posts["post_date"] >= w_start) & (shuffled_posts["post_date"] < w_end)
            if not w_mask.any():
                continue

            for ticker in shuffled_posts.loc[w_mask, "ticker"].unique():
                if ticker not in stock_dfs:
                    continue
                t_mask = w_mask & (shuffled_posts["ticker"] == ticker)
                n_signals = t_mask.sum()
                if n_signals == 0:
                    continue

                # Eligible dates within the window
                t_dates = stock_dfs[ticker].index
                t_dates_in_w = t_dates[(t_dates >= w_start) & (t_dates < w_end)]
                if len(t_dates_in_w) == 0:
                    continue # Fallback, shouldn't really happen if signals were generated

                chosen_dates = np.random.choice(t_dates_in_w, size=n_signals, replace=True)
                shuffled_posts.loc[t_mask, "post_date"] = chosen_dates

        p_trades = rb.run_backtest(custom_posts_df=shuffled_posts, stock_dfs_preloaded=stock_dfs, spy_close_preloaded=spy_close)
        pr, ps = compute_metrics(p_trades)
        pooled_permuted_rets.append(pr)
        pooled_permuted_sharpes.append(ps)

        for i, (w_start, w_end) in enumerate(windows):
            pw_trades = p_trades[(p_trades["post_date"] >= w_start) & (p_trades["post_date"] < w_end)]
            pwr, pws = compute_metrics(pw_trades)
            window_permuted_rets[i].append(pwr)

    pooled_permuted_rets = np.array(pooled_permuted_rets)
    pooled_permuted_sharpes = np.array(pooled_permuted_sharpes)

    beat_both = np.sum((pooled_permuted_rets >= real_pooled_ret) & (pooled_permuted_sharpes >= real_pooled_sharpe))
    p_value = beat_both / NUM_PERMUTATIONS

    windows_won = 0
    for i in range(len(windows)):
        p_median = np.median(window_permuted_rets[i])
        if real_window_rets[i] > p_median:
            windows_won += 1

    win_rate = windows_won / len(windows)

    print(f"Walk-Forward Pooled P-Value: {p_value:.4f}")
    print(f"Windows Won vs Permuted Median: {windows_won}/{len(windows)} ({win_rate*100:.1f}%)")

    return real_pooled_ret, real_pooled_sharpe, pooled_permuted_rets, pooled_permuted_sharpes, p_value, win_rate, len(windows)


def main():
    posts_df, stock_dfs, spy_close = load_base_data()

    is_real_ret, is_real_sharpe, is_p_rets, is_p_sharpes, is_pval = run_in_sample_test(posts_df, stock_dfs, spy_close)
    wf_real_ret, wf_real_sharpe, wf_p_rets, wf_p_sharpes, wf_pval, wf_win_rate, num_windows = run_walk_forward_test(posts_df, stock_dfs, spy_close)

    # Plotting
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # In-Sample Plot
    axes[0].hist(is_p_rets * 100, bins=30, color='skyblue', alpha=0.7, edgecolor='black', label="Permuted Returns")
    axes[0].axvline(is_real_ret * 100, color='red', linestyle='dashed', linewidth=2, label=f"Real Return ({is_real_ret*100:.2f}%)")
    axes[0].set_title(f"In-Sample Permutation Test\nP-value: {is_pval:.4f}", fontweight="bold")
    axes[0].set_xlabel("Total Return (%)")
    axes[0].set_ylabel("Frequency")
    axes[0].legend()

    # Walk-Forward Plot
    axes[1].hist(wf_p_rets * 100, bins=30, color='lightgreen', alpha=0.7, edgecolor='black', label="Permuted Returns")
    axes[1].axvline(wf_real_ret * 100, color='red', linestyle='dashed', linewidth=2, label=f"Real Pooled Return ({wf_real_ret*100:.2f}%)")
    axes[1].set_title(f"Walk-Forward Permutation Test\nP-value: {wf_pval:.4f}\nWin Rate vs Median: {wf_win_rate*100:.1f}%", fontweight="bold")
    axes[1].set_xlabel("Total Pooled Return (%)")
    axes[1].set_ylabel("Frequency")
    axes[1].legend()

    plt.tight_layout()
    plt.savefig("permutation_histogram.png", dpi=300)
    print("Histogram saved as permutation_histogram.png")

    print("\n" + "="*50)
    print("VALIDATION SUMMARY")
    print("="*50)
    print(f"In-Sample P-value: {is_pval:.4f}")
    print(f"Walk-Forward P-value: {wf_pval:.4f}")

    if is_pval > 0.01 or wf_pval > 0.05:
        print("\nCONCLUSION: this strategy has not demonstrated it beats random noise.")
    else:
        print("\nCONCLUSION: Strategy passed validation thresholds.")

if __name__ == "__main__":
    main()
