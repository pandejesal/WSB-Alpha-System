import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
import os

def compute_indicators(df):
    if len(df) < 20:
        return None
    df = df.copy()

    # 20 EMA
    df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()

    # 14 RSI
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    df["RSI_14"] = 100 - (100 / (1 + rs))

    # MACD
    ema_12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema_26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema_12 - ema_26
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]

    # Heikin-Ashi
    df["HA_Close"] = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4.0
    ha_open = np.zeros(len(df))
    ha_open[0] = (df["Open"].iloc[0] + df["Close"].iloc[0]) / 2.0
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + df["HA_Close"].iloc[i-1]) / 2.0
    df["HA_Open"] = ha_open
    df["HA_High"] = df[["High", "HA_Open", "HA_Close"]].max(axis=1)
    df["HA_Low"] = df[["Low", "HA_Open", "HA_Close"]].min(axis=1)

    # Bollinger Bands
    df["BB_Middle"] = df["Close"].rolling(window=20).mean()
    df["BB_Std"] = df["Close"].rolling(window=20).std().fillna(1e-4)
    df["BB_Upper"] = df["BB_Middle"] + 2.0 * df["BB_Std"]
    df["BB_Lower"] = df["BB_Middle"] - 2.0 * df["BB_Std"]
    df["BB_Middle"] = df["BB_Middle"].fillna(df["Close"])
    df["BB_Upper"] = df["BB_Upper"].fillna(df["Close"] * 1.05)
    df["BB_Lower"] = df["BB_Lower"].fillna(df["Close"] * 0.95)

    # Garman-Klass Volatility
    safe_high = df["High"].replace(0, 0.01)
    safe_low = df["Low"].replace(0, 0.01)
    safe_close = df["Close"].replace(0, 0.01)
    safe_open = df["Open"].replace(0, 0.01)

    log_hl = np.log(safe_high / safe_low)
    log_co = np.log(safe_close / safe_open)
    gk_element = 0.5 * (log_hl ** 2) - (2 * np.log(2) - 1) * (log_co ** 2)
    gk_variance = gk_element.rolling(window=20).mean()
    gk_variance = gk_variance.clip(lower=1e-10)
    df["GK_Vol"] = np.sqrt(252 * gk_variance)
    first_valid = df["GK_Vol"].dropna().iloc[0] if len(df["GK_Vol"].dropna()) > 0 else 0.50
    df["GK_Vol"] = df["GK_Vol"].fillna(first_valid)

    # VaR and CVaR (Rolling 20-day 95%)
    daily_pct_returns = df["Close"].pct_change().fillna(0)
    rolling_var = []
    rolling_cvar = []
    for i in range(len(df)):
        if i < 20:
            rolling_var.append(0.02)
            rolling_cvar.append(0.04)
        else:
            window_rets = daily_pct_returns.iloc[i-19:i+1]
            sorted_rets = np.sort(window_rets.values)
            var_idx = int(0.05 * len(sorted_rets))
            var_val = -sorted_rets[var_idx] if var_idx < len(sorted_rets) else 0.02
            losses_below_var = sorted_rets[:var_idx+1]
            cvar_val = -losses_below_var.mean() if len(losses_below_var) > 0 else 0.04
            rolling_var.append(max(var_val, 0.0))
            rolling_cvar.append(max(cvar_val, 0.0))

    df["VaR_95"] = rolling_var
    df["CVaR_95"] = rolling_cvar
    return df

def run_backtest():
    print("=" * 70)
    print("RUNNING HISTORICAL BACKTEST & PERFORMANCE OPTIMIZATION (2020 - 2026)")
    print("=" * 70)

    # Load generated historical posts
    posts_df = pd.read_csv("wsb_factual_research_data.csv")
    posts_df["post_date"] = pd.to_datetime(posts_df["post_date"])

    unique_tickers = posts_df["ticker"].unique().tolist()

    # Download pricing data
    min_date = posts_df["post_date"].min() - timedelta(days=60)
    max_date = posts_df["post_date"].max() + timedelta(days=140)

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

    FORWARD_DAYS = [1, 5, 10, 20, 30, 60, 90]

    # We will compute the returns for three strategies:
    # 1. Raw Sentiment (Static 5-day holding period)
    # 2. Tech Confluence Ensemble (Static 5-day holding period)
    # 3. Dynamic Volatility Regime Switching Confluence Strategy

    trades = []

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

        spy_entry_date = entry_date if entry_date in spy_close.index else spy_close.index[spy_close.index.searchsorted(entry_date, side="left")]
        spy_entry_px = spy_close.loc[spy_entry_date]

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

        # Volatility holding period regime
        regime_holding_days = 10 if gk_vol < 0.30 else 1

        # Precompute target exit returns for dynamic regime switching
        target_regime_idx = entry_idx + regime_holding_days
        if target_regime_idx < len(ind_df):
            regime_exit_date = ind_df.index[target_regime_idx]
            regime_exit_px = ind_df["Close"].iloc[target_regime_idx]
            regime_spy_exit_px = spy_close.loc[regime_exit_date] if regime_exit_date in spy_close.index else spy_close.iloc[min(spy_close.index.searchsorted(regime_exit_date, side="left"), len(spy_close)-1)]
            regime_stock_ret = (regime_exit_px - entry_px) / entry_px if sentiment_score > 0 else (entry_px - regime_exit_px) / entry_px
            regime_spy_ret = (regime_spy_exit_px - spy_entry_px) / spy_entry_px if sentiment_score > 0 else (spy_entry_px - regime_spy_exit_px) / spy_entry_px
        else:
            regime_stock_ret = None
            regime_spy_ret = None

        # Compile trade forward returns
        trade_metrics = {
            "post_date": post_date,
            "ticker": ticker,
            "sentiment_score": sentiment_score,
            "risk_parity_weight": risk_parity_weight,
            "regime_holding_days": regime_holding_days
        }

        for d in FORWARD_DAYS:
            target_idx = entry_idx + d
            if target_idx < len(ind_df):
                exit_date = ind_df.index[target_idx]
                exit_px = ind_df["Close"].iloc[target_idx]
                spy_exit_px = spy_close.loc[exit_date] if exit_date in spy_close.index else spy_close.iloc[min(spy_close.index.searchsorted(exit_date, side="left"), len(spy_close)-1)]

                # Actual stock and SPY returns (directional)
                stock_ret = (exit_px - entry_px) / entry_px if sentiment_score > 0 else (entry_px - exit_px) / entry_px
                spy_ret = (spy_exit_px - spy_entry_px) / spy_entry_px if sentiment_score > 0 else (spy_entry_px - spy_exit_px) / spy_entry_px

                trade_metrics[f"ret_{d}d"] = stock_ret
                trade_metrics[f"spy_ret_{d}d"] = spy_ret

                # Dynamic Regime Switching Strategy Return
                if confluence_triggered_full:
                    if d <= regime_holding_days:
                        trade_metrics[f"dynamic_ret_{d}d"] = stock_ret * risk_parity_weight
                    else:
                        if regime_stock_ret is not None:
                            trade_metrics[f"dynamic_ret_{d}d"] = regime_stock_ret * risk_parity_weight
                        else:
                            trade_metrics[f"dynamic_ret_{d}d"] = None
                else:
                    trade_metrics[f"dynamic_ret_{d}d"] = 0.0

                # Ensemble Only Return (Static 5-day holding period default)
                if confluence_triggered_ensemble_only:
                    # For static 5-day holding, if d <= 5 we take the return, else it locks at 5-day return
                    static_holding = 5
                    if d <= static_holding:
                        trade_metrics[f"ensemble_ret_{d}d"] = stock_ret * risk_parity_weight
                    else:
                        # 5-day return
                        idx_5 = entry_idx + 5
                        if idx_5 < len(ind_df):
                            ret_5 = (ind_df["Close"].iloc[idx_5] - entry_px) / entry_px if sentiment_score > 0 else (entry_px - ind_df["Close"].iloc[idx_5]) / entry_px
                            trade_metrics[f"ensemble_ret_{d}d"] = ret_5 * risk_parity_weight
                        else:
                            trade_metrics[f"ensemble_ret_{d}d"] = None
                else:
                    trade_metrics[f"ensemble_ret_{d}d"] = 0.0

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
                trade_metrics[f"dynamic_ret_{d}d"] = None
                trade_metrics[f"ensemble_ret_{d}d"] = None
                trade_metrics[f"raw_ret_{d}d"] = None

        trades.append(trade_metrics)

    trades_df = pd.DataFrame(trades)

    # Save the synchronized database
    posts_with_pricing = posts_df.merge(trades_df, on=["post_date", "ticker", "sentiment_score"], how="inner")
    posts_with_pricing.to_csv("wsb_factual_research_data.csv", index=False)

    print("\n" + "=" * 70)
    print("STRATEGY PERFORMANCE COMPARISON")
    print("=" * 70)

    horizons = {
        "Short-Term (1d)": ("raw_ret_1d", "ensemble_ret_1d", "dynamic_ret_1d"),
        "Short-Term (5d)": ("raw_ret_5d", "ensemble_ret_5d", "dynamic_ret_5d"),
        "Mid-Long Term (10d)": ("raw_ret_10d", "ensemble_ret_10d", "dynamic_ret_10d"),
        "Mid-Long Term (20d)": ("raw_ret_20d", "ensemble_ret_20d", "dynamic_ret_20d"),
        "Long-Term (30d)": ("raw_ret_30d", "ensemble_ret_30d", "dynamic_ret_30d"),
        "Long-Term (60d)": ("raw_ret_60d", "ensemble_ret_60d", "dynamic_ret_60d"),
        "Long-Term (90d)": ("raw_ret_90d", "ensemble_ret_90d", "dynamic_ret_90d"),
    }

    report_data = []

    for term, (raw_col, ens_col, dyn_col) in horizons.items():
        raw_mean = trades_df[raw_col].mean() * 100
        ens_mean = trades_df[ens_col].mean() * 100
        dyn_mean = trades_df[dyn_col].mean() * 100

        raw_win = (trades_df[raw_col] > 0).sum() / len(trades_df[raw_col].dropna()) * 100
        ens_win = (trades_df[ens_col] > 0).sum() / len(trades_df[ens_col].dropna()) * 100
        dyn_win = (trades_df[dyn_col] > 0).sum() / len(trades_df[dyn_col].dropna()) * 100

        # Annualized Sharpe (assuming ~100 trades a year)
        def sharpe(rets):
            std = rets.std()
            return (rets.mean() / (std + 1e-10)) * np.sqrt(100) if std > 0 else 0.0

        raw_sharpe = sharpe(trades_df[raw_col])
        ens_sharpe = sharpe(trades_df[ens_col])
        dyn_sharpe = sharpe(trades_df[dyn_col])

        report_data.append({
            "Term": term,
            "Raw Mean (%)": raw_mean,
            "Raw Win (%)": raw_win,
            "Raw Sharpe": raw_sharpe,
            "Ensemble Mean (%)": ens_mean,
            "Ensemble Win (%)": ens_win,
            "Ensemble Sharpe": ens_sharpe,
            "Dynamic Mean (%)": dyn_mean,
            "Dynamic Win (%)": dyn_win,
            "Dynamic Sharpe": dyn_sharpe,
        })

    report_df = pd.DataFrame(report_data)
    print(report_df.to_string(index=False, formatters={
        "Raw Mean (%)": "{:.2f}%".format,
        "Raw Win (%)": "{:.1f}%".format,
        "Raw Sharpe": "{:.2f}".format,
        "Ensemble Mean (%)": "{:.2f}%".format,
        "Ensemble Win (%)": "{:.1f}%".format,
        "Ensemble Sharpe": "{:.2f}".format,
        "Dynamic Mean (%)": "{:.2f}%".format,
        "Dynamic Win (%)": "{:.1f}%".format,
        "Dynamic Sharpe": "{:.2f}".format,
    }))

    # Cumulative Performance curves over time
    trades_sorted = trades_df.sort_values(by="post_date").reset_index(drop=True)

    # We choose the 5d return to represent Short-Term, 20d to represent Mid-Long Term, and 90d to represent Long-Term
    fig, axes = plt.subplots(3, 1, figsize=(12, 16))

    terms_to_plot = [
        ("Short-Term (5d)", "raw_ret_5d", "ensemble_ret_5d", "dynamic_ret_5d", 0),
        ("Mid-Long Term (20d)", "raw_ret_20d", "ensemble_ret_20d", "dynamic_ret_20d", 1),
        ("Long-Term (90d)", "raw_ret_90d", "ensemble_ret_90d", "dynamic_ret_90d", 2),
    ]

    for term, r_col, e_col, d_col, ax_idx in terms_to_plot:
        ax = axes[ax_idx]

        # Cumulative returns
        raw_cum = (1 + trades_sorted[r_col].fillna(0)).cumprod() - 1
        ens_cum = (1 + trades_sorted[e_col].fillna(0)).cumprod() - 1
        dyn_cum = (1 + trades_sorted[d_col].fillna(0)).cumprod() - 1

        ax.plot(trades_sorted["post_date"], raw_cum * 100, label=f"Raw Sentiment Strategy (Static 5d)", alpha=0.7, color="red")
        ax.plot(trades_sorted["post_date"], ens_cum * 100, label=f"Technical Confluence Strategy (Static 5d)", alpha=0.8, color="blue")
        ax.plot(trades_sorted["post_date"], dyn_cum * 100, label=f"Dynamic Volatility Regime Strategy", linewidth=2.5, color="green")

        ax.set_title(f"Cumulative Performance - {term} Horizon (2020-2026)", fontsize=12, fontweight="bold")
        ax.set_xlabel("Date")
        ax.set_ylabel("Cumulative Return (%)")
        ax.legend(loc="upper left")
        ax.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    plt.savefig("wsb_stock_trajectories.png", dpi=300)
    print("\nVisualization plot successfully generated & saved to: wsb_stock_trajectories.png")

    print("\n" + "=" * 70)
    print("MOST PROFITABLE ALGORITHM FINDINGS")
    print("=" * 70)
    for term, r_col, e_col, d_col, _ in terms_to_plot:
        r_tot = (1 + trades_sorted[r_col].fillna(0)).prod() - 1
        e_tot = (1 + trades_sorted[e_col].fillna(0)).prod() - 1
        d_tot = (1 + trades_sorted[d_col].fillna(0)).prod() - 1

        results = [("Raw Sentiment", r_tot), ("Technical Confluence", e_tot), ("Dynamic Volatility Regime", d_tot)]
        results.sort(key=lambda x: x[1], reverse=True)

        print(f"\nFor {term}:")
        for rank, (name, tot) in enumerate(results, 1):
            print(f"  {rank}. {name}: {tot * 100:.2f}% Total Return")
        print(f"  --> Most Profitable: {results[0][0]}")

if __name__ == "__main__":
    run_backtest()
