import pandas as pd
import numpy as np
import yfinance as yf
from datetime import timedelta
import matplotlib.pyplot as plt
from src.alpha.indicators import compute_indicators, compute_regime_returns







def evaluate_strategy_on_data(posts_df, stock_dfs, spy_close, return_type="total_return"):
    trades = []
    FORWARD_DAYS = [1, 5, 10, 20, 30, 60, 90, 120, 252, 300]

    for idx, row in posts_df.iterrows():
        ticker = row["ticker"]
        post_date = row["post_date"]
        sentiment_score = row["sentiment_score"]

        if ticker not in stock_dfs:
            continue

        ind_df = stock_dfs[ticker]
        entry_idx = ind_df.index.searchsorted(post_date, side="right")
        if entry_idx >= len(ind_df):
            continue

        entry_date = ind_df.index[entry_idx]
        entry_px = ind_df["Close"].iloc[entry_idx]
        entry_row = ind_df.iloc[entry_idx]

        spy_entry_idx = spy_close.index.searchsorted(entry_date, side="left")
        if spy_entry_idx >= len(spy_close):
            spy_entry_idx = len(spy_close) - 1
        spy_entry_px = spy_close.iloc[spy_entry_idx]

        gk_vol = entry_row.get("GK_Vol", 0.50)
        entry_cvar = entry_row.get("CVaR_95", 0.04)

        # Determine signals
        volatility_shield_passed = gk_vol < 1.20

        # Voting Channels
        alg_ha = False
        alg_momentum = False
        alg_reversion = False
        alg_bb = False

        if sentiment_score > 0:
            alg_ha = entry_row["HA_Close"] > entry_row["HA_Open"]
            alg_momentum = (entry_row["Close"] > entry_row["EMA_20"]) and (entry_row["MACD_Hist"] > 0.0)
            alg_reversion = (40.0 < entry_row["RSI_14"] < 70.0)
            alg_bb = entry_row["Close"] > entry_row["BB_Lower"]
        elif sentiment_score < 0:
            alg_ha = entry_row["HA_Close"] < entry_row["HA_Open"]
            alg_momentum = (entry_row["Close"] < entry_row["EMA_20"]) and (entry_row["MACD_Hist"] < 0.0)
            alg_reversion = (30.0 < entry_row["RSI_14"] < 60.0)
            alg_bb = entry_row["Close"] < entry_row["BB_Upper"]

        ensemble_score = int(alg_ha) + int(alg_momentum) + int(alg_reversion) + int(alg_bb)
        confluence_triggered_ensemble_only = (ensemble_score >= 3) and volatility_shield_passed

        # Risk Parity weight
        clipped_vol = max(min(gk_vol, 1.20), 0.15)
        sharpe_multiplier = 1.25 if ensemble_score == 4 else 1.0
        risk_parity_weight = (0.15 / clipped_vol) * sharpe_multiplier

        if entry_cvar > 0.15:
            risk_parity_weight *= 0.50

        # Forecaster consensus
        bb_pos = (entry_row["Close"] - entry_row["BB_Lower"]) / (entry_row["BB_Upper"] - entry_row["BB_Lower"] + 1e-10)
        rsi_mom = (entry_row["RSI_14"] - 50.0) / 50.0
        macd_mom = entry_row["MACD_Hist"] / (entry_row["Close"] + 1e-10)
        hist_5d_ret = (entry_row["Close"] - ind_df["Close"].iloc[max(0, entry_idx-5)]) / (ind_df["Close"].iloc[max(0, entry_idx-5)] + 1e-10)
        projected_5d_return = 0.40 * hist_5d_ret + 0.30 * macd_mom + 0.15 * rsi_mom + 0.15 * (bb_pos - 0.50)

        if confluence_triggered_ensemble_only and abs(projected_5d_return) > 0.02:
            risk_parity_weight *= 1.50

        forecast_passed = False
        if sentiment_score > 0 and projected_5d_return > 0.005:
            forecast_passed = True
        elif sentiment_score < 0 and projected_5d_return < -0.005:
            forecast_passed = True

        confluence_triggered_full = confluence_triggered_ensemble_only and forecast_passed

        # Compute holding periods for each Term Horizon
        short_holding_days = 10 if gk_vol < 0.30 else 1
        midlong_holding_days = 60 if gk_vol < 0.30 else 5
        longterm_holding_days = 252 if gk_vol < 0.30 else 10

        # S&P 500 Market Regime Detection for Auto-Regime Switching
        spy_window = spy_close.iloc[max(0, spy_entry_idx-19):spy_entry_idx+1]
        if spy_entry_idx >= 20:
            spy_ret_20d = (spy_entry_px - spy_close.iloc[spy_entry_idx-20]) / spy_close.iloc[spy_entry_idx-20]
            spy_pct_rets = spy_window.pct_change().dropna()
            spy_vol_20d = spy_pct_rets.std() * np.sqrt(252)
        else:
            spy_ret_20d = 0.05
            spy_vol_20d = 0.12

        # Assign optimal regime based on market rules
        if spy_ret_20d > 0 and spy_vol_20d < 0.15:
            adaptive_mode = "long_term"
            adaptive_holding_days = longterm_holding_days
        elif spy_ret_20d > 0 and 0.15 <= spy_vol_20d < 0.25:
            adaptive_mode = "mid_long_term"
            adaptive_holding_days = midlong_holding_days
        else:
            adaptive_mode = "short_term"
            adaptive_holding_days = short_holding_days

        # Precompute target exit returns for each strategy
        ret_stock_short, ret_spy_short = compute_regime_returns(ind_df, spy_close, entry_idx, entry_px, spy_entry_px, sentiment_score, short_holding_days)
        ret_stock_midlong, ret_spy_midlong = compute_regime_returns(ind_df, spy_close, entry_idx, entry_px, spy_entry_px, sentiment_score, midlong_holding_days)
        ret_stock_longterm, ret_spy_longterm = compute_regime_returns(ind_df, spy_close, entry_idx, entry_px, spy_entry_px, sentiment_score, longterm_holding_days)

        if adaptive_mode == "long_term":
            ret_stock_adaptive = ret_stock_longterm
        elif adaptive_mode == "mid_long_term":
            ret_stock_adaptive = ret_stock_midlong
        else:
            ret_stock_adaptive = ret_stock_short

        # Compile trade metrics
        trade_metrics = {
            "post_date": post_date,
            "ticker": ticker,
            "sentiment_score": sentiment_score,
            "risk_parity_weight": risk_parity_weight,
            "short_holding_days": short_holding_days,
            "midlong_holding_days": midlong_holding_days,
            "longterm_holding_days": longterm_holding_days,
            "adaptive_holding_days": adaptive_holding_days,
            "adaptive_mode": adaptive_mode
        }

        for d in FORWARD_DAYS:
            target_idx = entry_idx + d
            if target_idx < len(ind_df):
                exit_date = ind_df.index[target_idx]
                exit_px = ind_df["Close"].iloc[target_idx]
                spy_exit_px = spy_close.loc[exit_date] if exit_date in spy_close.index else spy_close.iloc[min(spy_close.index.searchsorted(exit_date, side="left"), len(spy_close)-1)]

                # Directional stock & S&P 500 returns
                stock_ret = (exit_px - entry_px) / entry_px if sentiment_score > 0 else (entry_px - exit_px) / entry_px
                spy_ret = (spy_exit_px - spy_entry_px) / spy_entry_px if sentiment_score > 0 else (spy_entry_px - spy_exit_px) / spy_entry_px

                trade_metrics[f"ret_{d}d"] = stock_ret
                trade_metrics[f"spy_ret_{d}d"] = spy_ret

                # Calculate returns under each Strategy Mode (cash preservation if confluence is not met)
                if confluence_triggered_full:
                    # Short-Term Mode
                    trade_metrics[f"short_ret_{d}d"] = stock_ret * risk_parity_weight if d <= short_holding_days else ret_stock_short * risk_parity_weight
                    # Mid-Long Term Mode
                    trade_metrics[f"midlong_ret_{d}d"] = stock_ret * risk_parity_weight if d <= midlong_holding_days else ret_stock_midlong * risk_parity_weight
                    # Long-Term Mode
                    trade_metrics[f"longterm_ret_{d}d"] = stock_ret * risk_parity_weight if d <= longterm_holding_days else ret_stock_longterm * risk_parity_weight
                    # Adaptive Switcher Mode
                    trade_metrics[f"adaptive_ret_{d}d"] = stock_ret * risk_parity_weight if d <= adaptive_holding_days else ret_stock_adaptive * risk_parity_weight
                else:
                    trade_metrics[f"short_ret_{d}d"] = 0.0
                    trade_metrics[f"midlong_ret_{d}d"] = 0.0
                    trade_metrics[f"longterm_ret_{d}d"] = 0.0
                    trade_metrics[f"adaptive_ret_{d}d"] = 0.0

                # Raw Sentiment Strategy (Static 5-day holding, no filters)
                static_holding = 5
                if d <= static_holding:
                    trade_metrics[f"raw_ret_{d}d"] = stock_ret
                else:
                    idx_5 = entry_idx + 5
                    if idx_5 < len(ind_df):
                        ret_5 = (ind_df["Close"].iloc[idx_5] - entry_px) / entry_px if sentiment_score > 0 else (entry_px - ind_df["Close"].iloc[idx_5]) / entry_px
                        trade_metrics[f"raw_ret_{d}d"] = ret_5
                    else:
                        trade_metrics[f"raw_ret_{d}d"] = None
            else:
                trade_metrics[f"ret_{d}d"] = None
                trade_metrics[f"spy_ret_{d}d"] = None
                trade_metrics[f"short_ret_{d}d"] = None
                trade_metrics[f"midlong_ret_{d}d"] = None
                trade_metrics[f"longterm_ret_{d}d"] = None
                trade_metrics[f"adaptive_ret_{d}d"] = None
                trade_metrics[f"raw_ret_{d}d"] = None

        trades.append(trade_metrics)


    trades_df = pd.DataFrame(trades)

    if return_type == "full_df":
        return trades_df
    elif return_type == "total_return":
        return trades_df["adaptive_ret_5d"].fillna(0).sum() if "adaptive_ret_5d" in trades_df else 0.0


def run_backtest(custom_posts_df=None, stock_dfs_preloaded=None, spy_close_preloaded=None):
    if custom_posts_df is None:
        print("=" * 70)
        print("RUNNING HISTORICAL BACKTEST & PERFORMANCE OPTIMIZATION (2020 - 2026)")
        print("=" * 70)

        # Load generated historical posts
        posts_df = pd.read_csv("wsb_factual_research_data.csv")
        posts_df["post_date"] = pd.to_datetime(posts_df["post_date"])
    else:
        posts_df = custom_posts_df.copy()

    unique_tickers = posts_df["ticker"].unique().tolist()

    if stock_dfs_preloaded is not None and spy_close_preloaded is not None:
        stock_dfs = stock_dfs_preloaded
        spy_close = spy_close_preloaded
    else:
        # Download pricing data - extended download window to cover 1-1.2 years holding periods
        min_date = posts_df["post_date"].min() - timedelta(days=60)
        max_date = posts_df["post_date"].max() + timedelta(days=450)

        print(f"Downloading historical stock data for {len(unique_tickers)} tickers + SPY from {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}...")
        px_data = yf.download(unique_tickers + ["SPY"], start=min_date, end=max_date, progress=False, auto_adjust=True)

        # Handle multi-index columns from yfinance
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

    FORWARD_DAYS = [1, 5, 10, 20, 30, 60, 90, 120, 252, 300]

    # We will compute the returns for five strategies:
    # 1. Raw Sentiment (Static 5-day holding period)
    # 2. Short-Term Adaptive Confluence Strategy (Dynamic 10d/1d holding period)
    # 3. Mid-Long Term Adaptive Confluence Strategy (Dynamic 60d/5d holding period)
    # 4. Long-Term Adaptive Confluence Strategy (Dynamic 252d/10d holding period)
    # 5. S&P 500 Adaptive Auto-Regime Switcher (dynamically selects optimal strategy based on SPY trend & volatility)


    trades_df = evaluate_strategy_on_data(posts_df, stock_dfs, spy_close, return_type="full_df")

    if custom_posts_df is not None:
        # For validation harness, return only the metrics needed (total return & sharpe of adaptive strategy)
        if "adaptive_ret_5d" not in trades_df: # arbitrary check for existance
            return 0.0, 0.0, trades_df

        # Determine which holding period is the primary focus of the aggregate metrics
        # The adaptive returns dynamically switch between horizons, but the trades_df has daily columns
        # To make it fair and robust across all horizons, we'll look at the realized returns
        # Actually, in run_backtest, they sort and cumsum 'adaptive_ret_X'. Let's pick 5d, 60d, 252d.
        # However, run_backtest's 'return_type="total_return"' returns trades_df["adaptive_ret_5d"].fillna(0).sum()
        # For the validation harness, we'll compute total return and sharpe using the adaptive strategy.
        # To avoid being tied to a specific Xd column if it doesn't represent the true holding well,
        # let's just pick one representative column, or return the full trades_df and compute it in validation.py
        return trades_df

    # Save the synchronized database
    posts_with_pricing = posts_df.merge(trades_df, on=["post_date", "ticker", "sentiment_score"], how="inner")
    posts_with_pricing.to_csv("wsb_factual_research_data.csv", index=False)

    print("\n" + "=" * 70)
    print("STRATEGY PERFORMANCE COMPARISON")
    print("=" * 70)

    # Horizons to display
    horizons = {
        "Short-Term Horizon (5d)": ("raw_ret_5d", "short_ret_5d", "midlong_ret_5d", "longterm_ret_5d", "adaptive_ret_5d"),
        "Mid-Long Horizon (60d)": ("raw_ret_60d", "short_ret_60d", "midlong_ret_60d", "longterm_ret_60d", "adaptive_ret_60d"),
        "Long-Term Horizon (252d)": ("raw_ret_252d", "short_ret_252d", "midlong_ret_252d", "longterm_ret_252d", "adaptive_ret_252d"),
    }

    report_data = []

    for term, (raw_col, s_col, m_col, l_col, a_col) in horizons.items():
        raw_mean = trades_df[raw_col].mean() * 100
        s_mean = trades_df[s_col].mean() * 100
        m_mean = trades_df[m_col].mean() * 100
        l_mean = trades_df[l_col].mean() * 100
        a_mean = trades_df[a_col].mean() * 100

        raw_win = (trades_df[raw_col] > 0).sum() / len(trades_df[raw_col].dropna()) * 100
        s_win = (trades_df[s_col] > 0).sum() / len(trades_df[s_col].dropna()) * 100
        m_win = (trades_df[m_col] > 0).sum() / len(trades_df[m_col].dropna()) * 100
        l_win = (trades_df[l_col] > 0).sum() / len(trades_df[l_col].dropna()) * 100
        a_win = (trades_df[a_col] > 0).sum() / len(trades_df[a_col].dropna()) * 100

        def sharpe(rets):
            std = rets.std()
            return (rets.mean() / (std + 1e-10)) * np.sqrt(100) if std > 0 else 0.0

        raw_sharpe = sharpe(trades_df[raw_col])
        s_sharpe = sharpe(trades_df[s_col])
        m_sharpe = sharpe(trades_df[m_col])
        l_sharpe = sharpe(trades_df[l_col])
        a_sharpe = sharpe(trades_df[a_col])

        report_data.append({
            "Horizon": term,
            "Raw Return": f"{raw_mean:.2f}% (WR: {raw_win:.1f}%, SR: {raw_sharpe:.2f})",
            "Short-Term": f"{s_mean:.2f}% (WR: {s_win:.1f}%, SR: {s_sharpe:.2f})",
            "Mid-Long": f"{m_mean:.2f}% (WR: {m_win:.1f}%, SR: {m_sharpe:.2f})",
            "Long-Term": f"{l_mean:.2f}% (WR: {l_win:.1f}%, SR: {l_sharpe:.2f})",
            "Adaptive Switcher": f"{a_mean:.2f}% (WR: {a_win:.1f}%, SR: {a_sharpe:.2f})",
        })

    report_df = pd.DataFrame(report_data)
    print(report_df.to_string(index=False))

    # Cumulative Performance curves over time
    trades_sorted = trades_df.sort_values(by="post_date").reset_index(drop=True)

    fig, axes = plt.subplots(2, 2, figsize=(18, 14))

    terms_to_plot = [
        ("Short-Term (5d) Horizon", "raw_ret_5d", "short_ret_5d", "adaptive_ret_5d", "Short-Term Strategy", axes[0, 0]),
        ("Mid-Long (60d) Horizon", "raw_ret_60d", "midlong_ret_60d", "adaptive_ret_60d", "Mid-Long Strategy", axes[0, 1]),
        ("Long-Term (252d) Horizon", "raw_ret_252d", "longterm_ret_252d", "adaptive_ret_252d", "Long-Term Strategy", axes[1, 0]),
    ]

    for term, r_col, spec_col, a_col, spec_name, ax in terms_to_plot:
        # Cumulative returns (Simple sum portfolio model)
        raw_cum = trades_sorted[r_col].fillna(0).cumsum()
        spec_cum = trades_sorted[spec_col].fillna(0).cumsum()
        a_cum = trades_sorted[a_col].fillna(0).cumsum()

        ax.plot(trades_sorted["post_date"], raw_cum * 100, label="Raw Sentiment Strategy (Static 5d)", alpha=0.6, color="red")
        ax.plot(trades_sorted["post_date"], spec_cum * 100, label=f"{spec_name} (Dynamic Volatility Regime)", alpha=0.8, color="blue")
        ax.plot(trades_sorted["post_date"], a_cum * 100, label="S&P 500 Adaptive Auto-Regime Switcher", linewidth=2.5, color="green")

        ax.set_title(f"Cumulative Performance - {term} (2020-2026)", fontsize=12, fontweight="bold")
        ax.set_xlabel("Date")
        ax.set_ylabel("Cumulative Return (%)")
        ax.legend(loc="upper left")
        ax.grid(True, linestyle="--", alpha=0.5)

    # 4th Subplot: Growth of a $100 Initial Investment over Forward Intervals (1d to 300d)
    ax_grow = axes[1, 1]
    horizons_grow = [0] + FORWARD_DAYS
    raw_vals = [100.0]
    short_vals = [100.0]
    midlong_vals = [100.0]
    longterm_vals = [100.0]
    adaptive_vals = [100.0]
    spy_vals = [100.0]

    for d in FORWARD_DAYS:
        raw_vals.append(100.0 * (1 + trades_sorted[f"raw_ret_{d}d"].fillna(0).mean()))
        short_vals.append(100.0 * (1 + trades_sorted[f"short_ret_{d}d"].fillna(0).mean()))
        midlong_vals.append(100.0 * (1 + trades_sorted[f"midlong_ret_{d}d"].fillna(0).mean()))
        longterm_vals.append(100.0 * (1 + trades_sorted[f"longterm_ret_{d}d"].fillna(0).mean()))
        adaptive_vals.append(100.0 * (1 + trades_sorted[f"adaptive_ret_{d}d"].fillna(0).mean()))
        spy_vals.append(100.0 * (1 + trades_sorted[f"spy_ret_{d}d"].fillna(0).mean()))

    ax_grow.plot(horizons_grow, raw_vals, label="Raw Sentiment (Static 5d)", color="red", marker="o", linestyle="-", alpha=0.7)
    ax_grow.plot(horizons_grow, short_vals, label="Short-Term (Dynamic 10d/1d)", color="orange", marker="s", linestyle="-", alpha=0.7)
    ax_grow.plot(horizons_grow, midlong_vals, label="Mid-Long (Dynamic 60d/5d)", color="blue", marker="v", linestyle="-", alpha=0.7)
    ax_grow.plot(horizons_grow, longterm_vals, label="Long-Term (Dynamic 252d/10d)", color="purple", marker="^", linestyle="-", alpha=0.7)
    ax_grow.plot(horizons_grow, adaptive_vals, label="S&P 500 Adaptive Auto-Regime Switcher", color="green", marker="D", linewidth=2.5)
    ax_grow.plot(horizons_grow, spy_vals, label="S&P 500 Benchmark (SPY)", color="black", marker="x", linestyle="--")

    ax_grow.set_title("Growth of a $100 Initial Investment over Forward Intervals", fontsize=12, fontweight="bold")
    ax_grow.set_xlabel("Holding Period Days Offset (Intervals)")
    ax_grow.set_ylabel("Expected Portfolio Value ($)")
    ax_grow.legend(loc="upper left", fontsize=8)
    ax_grow.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    plt.savefig("wsb_stock_trajectories.png", dpi=300)
    print("\nVisualization plot successfully generated & saved to: wsb_stock_trajectories.png")

    print("\n" + "=" * 70)
    print("MOST PROFITABLE ALGORITHM FINDINGS")
    print("=" * 70)
    for term, r_col, spec_col, a_col, spec_name, _ in terms_to_plot:
        r_tot = trades_sorted[r_col].fillna(0).sum()
        spec_tot = trades_sorted[spec_col].fillna(0).sum()
        a_tot = trades_sorted[a_col].fillna(0).sum()

        results = [("Raw Sentiment", r_tot), (spec_name, spec_tot), ("Adaptive Switcher", a_tot)]
        results.sort(key=lambda x: x[1], reverse=True)

        print(f"\nFor {term}:")
        for rank, (name, tot) in enumerate(results, 1):
            print(f"  {rank}. {name}: {tot * 100:.2f}% Total Return")
        print(f"  --> Most Profitable: {results[0][0]}")

if __name__ == "__main__":
    run_backtest()