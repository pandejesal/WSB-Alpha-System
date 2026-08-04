import re

with open("scripts/comprehensive_backtest_report.py", "r") as f:
    content = f.read()

# Replace the opening logic to rank by ROC_60
opening_logic = """        # 3. Open new positions (T+1 execution meaning we use yesterday's signal for today's entry)
        if i > 0:
            prev_date = trading_days[i-1]

            if len(portfolio.open_positions) < max_positions:

                # Gather all candidates for today
                candidates = []
                for ticker, signals in signals_dict.items():
                    if prev_date in signals.index and signals.loc[prev_date]:
                        # Ensure we don't already have this position
                        if any(p['ticker'] == ticker for p in portfolio.open_positions):
                            continue

                        # Also check Macro Trend Filter (SPY 200 EMA Regime Shield)
                        # We only allow LONG position entries when SPY Close > SPY 200 EMA on prev_date
                        if prev_date in spy_df.index:
                            spy_close = spy_df.loc[prev_date, 'Close']
                            spy_ema_200 = spy_df.loc[prev_date, 'EMA_200']
                            if spy_close <= spy_ema_200:
                                continue # Block entry due to Macro Trend Filter

                        df = df_dict[ticker]
                        if prev_date in df.index:
                            roc_60 = df.loc[prev_date, "ROC_60"]
                            if pd.isna(roc_60):
                                roc_60 = -999 # penalize missing ROC
                            candidates.append({
                                'ticker': ticker,
                                'roc_60': roc_60
                            })

                # Rank candidates by 60-day relative strength (Momentum)
                candidates.sort(key=lambda x: x['roc_60'], reverse=True)

                for candidate in candidates:
                    if len(portfolio.open_positions) >= max_positions:
                        break

                    ticker = candidate['ticker']

                    # Execute trade today
                    if ticker in current_prices:
                        entry_price_raw = current_prices[ticker]
                        df = df_dict[ticker]

                        # Regime
                        gk = df.loc[prev_date, "GK_Vol"] if prev_date in df.index else 0.3"""

content = re.sub(
    r"        # 3\. Open new positions \(T\+1 execution meaning we use yesterday's signal for today's entry\)\n\s*if i > 0:\n\s*prev_date = trading_days\[i-1\]\n\n\s*if len\(portfolio\.open_positions\) < max_positions:\n\s*for ticker, signals in signals_dict\.items\(\):\n\s*if len\(portfolio\.open_positions\) >= max_positions:\n\s*break\n\n\s*# Check if signal fired yesterday\n\s*if prev_date in signals\.index and signals\.loc\[prev_date\]:\n\s*# Ensure we don't already have this position\n\s*if any\(p\['ticker'\] == ticker for p in portfolio\.open_positions\):\n\s*continue\n\n\s*# Execute trade today\n\s*if ticker in current_prices:\n\s*entry_price_raw = current_prices\[ticker\]\n\s*df = df_dict\[ticker\]\n\n\s*# Regime\n\s*gk = df\.loc\[prev_date, \"GK_Vol\"\] if prev_date in df\.index else 0\.3",
    opening_logic,
    content,
    flags=re.DOTALL
)

with open("scripts/comprehensive_backtest_report.py", "w") as f:
    f.write(content)
