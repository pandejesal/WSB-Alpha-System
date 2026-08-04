import re

with open("scripts/comprehensive_backtest_report.py", "r") as f:
    content = f.read()

# Update opening logic for Risk Parity sizing and ATR state
open_logic_orig = """                        # Regime
                        gk = df.loc[prev_date, "GK_Vol"] if prev_date in df.index else 0.3
                        if gk < 0.20:
                            regime = "low_volatility"
                        elif gk < 0.50:
                            regime = "normal"
                        else:
                            regime = "high_volatility"

                        slippage_pct = get_slippage(ticker)
                        entry_price = entry_price_raw * (1 + slippage_pct)

                        # Max 25% of equity per position
                        max_invest = portfolio.equity * max_pos_size_pct
                        # Limit by available cash
                        actual_invest = min(max_invest, portfolio.cash)

                        if actual_invest > 5: # Minimum $5 investment to make sense
                            qty = actual_invest / entry_price

                            spread_pct = 0.0005
                            spread_cost = entry_price * qty * spread_pct
                            cost = (entry_price * qty) + spread_cost

                            portfolio.open_position(ticker, qty, entry_price, cost, date_str, regime, holding_days, spread_cost)"""

open_logic_new = """                        # Regime
                        gk = df.loc[prev_date, "GK_Vol"] if prev_date in df.index else 0.3
                        if gk < 0.20:
                            regime = "low_volatility"
                        elif gk < 0.50:
                            regime = "normal"
                        else:
                            regime = "high_volatility"

                        slippage_pct = get_slippage(ticker)
                        entry_price = entry_price_raw * (1 + slippage_pct)
                        atr_14 = df.loc[prev_date, "ATR_14"] if prev_date in df.index and not pd.isna(df.loc[prev_date, "ATR_14"]) else (entry_price * 0.02)

                        # Volatility Risk Parity Sizing
                        # Position Shares = (Portfolio Equity * 0.02) / (Trailing_Mult * ATR_14)
                        risk_per_trade = portfolio.equity * 0.02
                        qty = risk_per_trade / (atr_trailing_mult * atr_14)

                        notional_value = qty * entry_price

                        # Max 25% of equity per position
                        max_invest = portfolio.equity * max_pos_size_pct

                        if notional_value > max_invest:
                            notional_value = max_invest
                            qty = notional_value / entry_price

                        # Limit by available cash
                        if notional_value > portfolio.cash:
                            notional_value = portfolio.cash
                            qty = notional_value / entry_price

                        if notional_value > 5: # Minimum $5 investment to make sense
                            spread_pct = 0.0005
                            spread_cost = entry_price * qty * spread_pct
                            cost = (entry_price * qty) + spread_cost

                            portfolio.open_position(ticker, qty, entry_price, cost, date_str, regime, holding_days, spread_cost, atr_14)"""

content = content.replace(open_logic_orig, open_logic_new)

with open("scripts/comprehensive_backtest_report.py", "w") as f:
    f.write(content)
