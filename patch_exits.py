import re

with open("scripts/comprehensive_backtest_report.py", "r") as f:
    content = f.read()

# 1. Update Portfolio.open_position to include highest_high, atr_14, etc.
open_pos_orig = """    def open_position(self, ticker, qty, entry_price, cost, date, regime, holding_days, spread_cost):
        self.cash -= cost
        self.open_positions.append({
            'ticker': ticker,
            'qty': qty,
            'entry_price': entry_price,
            'cost': cost,
            'entry_date': date,
            'regime': regime,
            'holding_days': holding_days,
            'days_held': 0,
            'spread_cost_entry': spread_cost
        })"""

open_pos_new = """    def open_position(self, ticker, qty, entry_price, cost, date, regime, holding_days, spread_cost, atr_14=0.0):
        self.cash -= cost
        self.open_positions.append({
            'ticker': ticker,
            'qty': qty,
            'entry_price': entry_price,
            'highest_high': entry_price,
            'atr_14': atr_14,
            'cost': cost,
            'entry_date': date,
            'regime': regime,
            'holding_days': holding_days,
            'days_held': 0,
            'spread_cost_entry': spread_cost
        })"""
content = content.replace(open_pos_orig, open_pos_new)

# 2. Update Portfolio.update_daily to maintain highest_high
update_daily_orig = """    def update_daily(self, date, current_prices):
        # Update days held
        for pos in self.open_positions:
            pos['days_held'] += 1

        # Calculate current equity
        pos_value = 0
        for pos in self.open_positions:
            current_price = current_prices.get(pos['ticker'], pos['entry_price'])
            pos_value += pos['qty'] * current_price"""

update_daily_new = """    def update_daily(self, date, current_prices, current_highs=None):
        if current_highs is None:
            current_highs = current_prices

        # Update days held and highest high
        for pos in self.open_positions:
            pos['days_held'] += 1
            if pos['ticker'] in current_highs:
                high_price = current_highs[pos['ticker']]
                if high_price > pos['highest_high']:
                    pos['highest_high'] = high_price

        # Calculate current equity
        pos_value = 0
        for pos in self.open_positions:
            current_price = current_prices.get(pos['ticker'], pos['entry_price'])
            pos_value += pos['qty'] * current_price"""
content = content.replace(update_daily_orig, update_daily_new)

with open("scripts/comprehensive_backtest_report.py", "w") as f:
    f.write(content)
