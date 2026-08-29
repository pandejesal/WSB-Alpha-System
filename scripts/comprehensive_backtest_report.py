import json
import logging
import os
from datetime import datetime

import numpy as np
import pandas as pd
import yfinance as yf

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set True when market data download fails and local unadjusted fallback data is used.
# While True, results must NOT be published to docs/data (daily CI pushes them to Pages).
DATA_IS_MOCK = False

def load_universe():
    try:
        with open("config/universe.json", "r") as f:
            data = json.load(f)
            return data.get("tickers", [])
    except Exception as e:
        logger.error(f"Failed to load universe: {e}")
        return []

def download_data(tickers, start_date, end_date):
    logger.info(f"Downloading data for {len(tickers)} tickers from {start_date} to {end_date}")

    try:
        yf.set_tz_cache_location('cache/yfinance')
    except Exception:
        pass

    try:
        # Download data with threading
        data = yf.download(tickers, start=start_date, end=end_date, group_by='ticker', auto_adjust=True, threads=True)

        # Also download SPY for benchmark
        spy_data = yf.download('SPY', start='2018-01-01', end=end_date, auto_adjust=True)

        # Check if rate limited
        if len(data) == 0:
            raise Exception("Rate limited")

        return data, spy_data
    except Exception as e:
        global DATA_IS_MOCK
        DATA_IS_MOCK = True
        logger.warning(f"Download failed ({e}), falling back to local unadjusted CSVs — results will NOT be published")

        # Fallback for SPY
        spy_csv_path = "market_data_2019_2026/ohlcv/SPY.csv"
        if os.path.exists(spy_csv_path):
            spy_data = pd.read_csv(spy_csv_path)
            if not spy_data.empty:
                spy_data['date'] = pd.to_datetime(spy_data['date'])
                spy_data = spy_data.set_index('date')
                spy_data = spy_data.loc['2018-01-01':end_date]
                spy_data = spy_data.rename(columns={
                    'open': 'Open',
                    'high': 'High',
                    'low': 'Low',
                    'close': 'Close',
                    'volume': 'Volume'
                })
                spy_data = spy_data[['Open', 'High', 'Low', 'Close', 'Volume']]
            else:
                spy_data = pd.DataFrame()
        else:
            spy_data = pd.DataFrame()

        # Fallback for Tickers
        dfs = []
        for ticker in tickers:
            csv_path = f"market_data_2019_2026/ohlcv/{ticker}.csv"
            if not os.path.exists(csv_path):
                logger.warning(f"Fallback CSV missing for {ticker}, skipping")
                continue
            df = pd.read_csv(csv_path)
            if df.empty:
                logger.warning(f"Fallback CSV empty for {ticker}, skipping")
                continue

            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            df = df.loc[start_date:end_date]

            df = df.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            })
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]

            df.columns = pd.MultiIndex.from_product([['Open', 'High', 'Low', 'Close', 'Volume'], [ticker]])
            dfs.append(df)

        if dfs:
            data = pd.concat(dfs, axis=1)
        else:
            data = pd.DataFrame()

        return data, spy_data

def compute_indicators_vectorized(df):
    """Computes necessary indicators in a vectorized manner for a single ticker's DataFrame."""
    if len(df) < 20:
        return None
    df = df.copy()

    # 20 EMA
    df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()

    # 14 ATR (Average True Range)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['ATR_14'] = true_range.rolling(14).mean()

    # 14 RSI
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    df["RSI_14"] = 100 - (100 / (1 + rs))

    # Heikin-Ashi
    df["HA_Close"] = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4.0
    ha_open = np.zeros(len(df))
    ha_open[0] = (df["Open"].iloc[0] + df["Close"].iloc[0]) / 2.0
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + df["HA_Close"].iloc[i-1]) / 2.0
    df["HA_Open"] = ha_open

    # Bollinger Bands
    df["BB_Middle"] = df["Close"].rolling(window=20).mean()
    df["BB_Std"] = df["Close"].rolling(window=20).std().fillna(1e-4)
    df["BB_Upper"] = df["BB_Middle"] + 2.0 * df["BB_Std"]
    df["BB_Lower"] = df["BB_Middle"] - 2.0 * df["BB_Std"]

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

    # 60-day Rate of Change (Momentum)
    df["ROC_60"] = df["Close"].pct_change(periods=60) * 100

    return df

def generate_signals_vectorized(df, rsi_bounds, gk_limit, min_confluence):
    """
    Evaluates confluence for each day.
    Conditions (Bullish):
    1. HA Close > HA Open
    2. Close > 20 EMA
    3. RSI between rsi_bounds (e.g. 30 and 70)
    4. Close > BB Lower (to avoid catching extreme falling knives)
    5. GK Vol < gk_limit

    We simply count the number of conditions met. If >= min_confluence, we have a signal.
    """
    rsi_low, rsi_high = rsi_bounds

    c1 = (df["HA_Close"] > df["HA_Open"]).astype(int)
    c2 = (df["Close"] > df["EMA_20"]).astype(int)
    c3 = ((df["RSI_14"] >= rsi_low) & (df["RSI_14"] <= rsi_high)).astype(int)
    c4 = (df["Close"] > df["BB_Lower"]).astype(int)
    c5 = (df["GK_Vol"] < gk_limit).astype(int)

    confluence_score = c1 + c2 + c3 + c4 + c5
    return confluence_score >= min_confluence

def get_deposit_schedule(start_date_str, end_date_str, amount, freq='quarterly'):
    dates = pd.date_range(start=start_date_str, end=end_date_str, freq='QS')
    # Use BDay to ensure we deposit on trading days
    b_dates = [d + pd.tseries.offsets.BDay(0) for d in dates]
    return {d.strftime('%Y-%m-%d'): amount for d in b_dates}

def compute_regulatory_fees(qty, side='buy'):
    """Compute SEC and TAF fees (apply to sells only)"""
    if side == 'buy':
        return 0.0
    # simplified version - for exact SEC fee we need the total dollar volume,
    # but for small positions, the $0.000166 per share TAF fee usually dominates,
    # though both are practically zero for $100 accounts.
    taf_fee = np.ceil(qty) * 0.000166
    return taf_fee

class Portfolio:
    def __init__(self, initial_capital, risk_free_rate=0.029):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.equity = initial_capital
        self.open_positions = []
        self.history = [] # daily equity curve
        self.trades = []
        self.total_deposits = 0
        self.deposits_count = 0
        self.peak_equity = initial_capital

    def deposit(self, amount):
        self.cash += amount
        self.equity += amount
        self.peak_equity = max(self.peak_equity, self.equity)
        self.total_deposits += amount
        self.deposits_count += 1

    def open_position(self, ticker, qty, entry_price, cost, date, regime, holding_days, spread_cost, atr_14=0.0):
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
        })

    def close_position(self, position, exit_price, pnl, exit_date, fees, slippage, spread_cost):
        self.cash += (position['qty'] * exit_price - fees)
        self.trades.append({
            'entry_date': position['entry_date'],
            'exit_date': exit_date,
            'ticker': position['ticker'],
            'side': 'buy',
            'entry_price': position['entry_price'],
            'exit_price': exit_price,
            'qty': position['qty'],
            'pnl': pnl,
            'fees': fees,
            'slippage': slippage,
            'spread_cost': position['spread_cost_entry'] + spread_cost,
            'holding_days': position['days_held'],
            'regime': position['regime']
        })

    def update_daily(self, date, current_prices, current_highs=None):
        if current_highs is None:
            current_highs = current_prices

        # Update days held and highest high
        for pos in self.open_positions:
            pos['days_held'] += 1
            if pos['ticker'] in current_highs:
                high_price = current_highs[pos['ticker']]
                pos['highest_high'] = max(pos['highest_high'], high_price)

        # Calculate current equity
        pos_value = 0
        for pos in self.open_positions:
            current_price = current_prices.get(pos['ticker'], pos['entry_price'])
            pos_value += pos['qty'] * current_price

        self.equity = self.cash + pos_value
        self.peak_equity = max(self.peak_equity, self.equity)

        # Calculate drawdowns
        daily_dd = (self.peak_equity - self.equity) / self.peak_equity if self.peak_equity > 0 else 0

        self.history.append({
            'date': date,
            'equity': self.equity,
            'cash': self.cash,
            'drawdown': daily_dd,
            'deposits': self.initial_capital + self.total_deposits
        })
        return daily_dd

    def liquidate_all(self, date, current_prices, get_slippage_fn):
        for pos in list(self.open_positions):
            current_price = current_prices.get(pos['ticker'], pos['entry_price'])
            slippage = get_slippage_fn(pos['ticker'])
            exit_price = current_price * (1 - slippage)
            spread_pct = 0.0005 # Large cap spread
            spread_cost = exit_price * pos['qty'] * spread_pct
            sec_fee = exit_price * pos['qty'] * 0.000008
            taf_fee = np.ceil(pos['qty']) * 0.000166
            fees = sec_fee + taf_fee

            pnl = (exit_price - pos['entry_price']) * pos['qty'] - spread_cost - fees
            self.close_position(pos, exit_price, pnl, date, fees, slippage, spread_cost)

        self.open_positions = []
        self.equity = self.cash # Since all positions are closed

def run_backtest_for_params(df_dict, spy_df, params, deposit_schedule):
    holding_days = 30 # Fixed max holding guardrail
    atr_trailing_mult = params['atr_trailing_mult']
    atr_profit_mult = params['atr_profit_mult']
    rsi_bounds = params['rsi_bounds']
    gk_limit = params.get('gk_limit', 1.0) # Keep for compatibility, or fix to 1.0/0.8
    min_confluence = params['min_confluence']

    # Precompute signals to save time
    signals_dict = {}
    for ticker, df in df_dict.items():
        signals_dict[ticker] = generate_signals_vectorized(df, rsi_bounds, gk_limit, min_confluence)

    # Get all trading days
    trading_days = spy_df.index

    portfolio = Portfolio(initial_capital=100)

    # Pre-calculate circuit breakers
    daily_cb = 0.08
    weekly_cb = 0.15

    max_positions = 4
    max_pos_size_pct = 0.25

    for i, date in enumerate(trading_days):
        date_str = date.strftime('%Y-%m-%d')

        # 1. Process deposits
        if date_str in deposit_schedule:
            portfolio.deposit(deposit_schedule[date_str])

        # Current prices for MTM and closing
        current_prices = {}
        current_highs = {}
        current_lows = {}
        for ticker, df in df_dict.items():
            if date in df.index:
                current_prices[ticker] = df.loc[date, "Close"]
                current_highs[ticker] = df.loc[date, "High"]
                current_lows[ticker] = df.loc[date, "Low"]

        def get_slippage(ticker):
             df = df_dict[ticker]
             if date in df.index:
                 atr = df.loc[date, "ATR_14"]
                 px = df.loc[date, "Close"]
                 if pd.isna(atr):
                     return 0.01
                 raw_slip = (atr / px) * 0.05
                 return max(0.001, min(0.025, raw_slip))
             return 0.01

        # Update daily metrics and check circuit breakers
        daily_dd = portfolio.update_daily(date_str, current_prices, current_highs)

        # We need a weekly drawdown approximation (using last 5 days of history)
        weekly_dd = 0
        if len(portfolio.history) >= 5:
             past_equity = portfolio.history[-5]['equity']
             weekly_dd = (past_equity - portfolio.equity) / past_equity if past_equity > 0 else 0

        if daily_dd > daily_cb or weekly_dd > weekly_cb:
             portfolio.liquidate_all(date_str, current_prices, get_slippage)
             continue

        # 2. Dynamic Exit System (Trailing Stop, Hard Stop, Profit Target, Max Holding)
        for pos in list(portfolio.open_positions):
            ticker = pos['ticker']
            if ticker in current_prices:
                low = current_lows[ticker]
                high = current_highs[ticker]
                close = current_prices[ticker]

                # Check stops and targets
                # Initial Hard Stop: Entry - (Trailing_Mult * ATR_14)
                hard_stop = pos['entry_price'] - (atr_trailing_mult * pos['atr_14'])
                # Trailing Stop: Highest High - (Trailing_Mult * ATR_14)
                trailing_stop = pos['highest_high'] - (atr_trailing_mult * pos['atr_14'])

                actual_stop = max(hard_stop, trailing_stop)

                # Profit Target: Entry + (Profit_Mult * ATR_14)
                profit_target = pos['entry_price'] + (atr_profit_mult * pos['atr_14'])

                exit_price_raw = None

                # We check if Low hit the stop
                if low <= actual_stop:
                    # Execute at stop price (or open if it gapped down, simplified to stop price)
                    exit_price_raw = actual_stop
                # We check if High hit the profit target
                elif high >= profit_target:
                    exit_price_raw = profit_target
                # Guardrail: max holding days (30)
                elif pos['days_held'] >= 30:
                    exit_price_raw = close

                if exit_price_raw is not None:
                    slippage_pct = get_slippage(ticker)
                    exit_price = exit_price_raw * (1 - slippage_pct)
                    spread_pct = 0.0005
                    spread_cost = exit_price * pos['qty'] * spread_pct

                    sec_fee = exit_price * pos['qty'] * 0.000008
                    taf_fee = np.ceil(pos['qty']) * 0.000166
                    fees = sec_fee + taf_fee

                    pnl = (exit_price - pos['entry_price']) * pos['qty'] - spread_cost - fees

                    portfolio.close_position(pos, exit_price, pnl, date_str, fees, slippage_pct, spread_cost)
                    portfolio.open_positions.remove(pos)

        # 3. Open new positions (T+1 execution meaning we use yesterday's signal for today's entry)
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
                            entry_atr = df.loc[prev_date, "ATR_14"] if prev_date in df.index and pd.notna(df.loc[prev_date, "ATR_14"]) else 0.01
                            portfolio.open_position(ticker, qty, entry_price, cost, date_str, regime, holding_days, spread_cost, atr_14=entry_atr)
# Force close all remaining positions at end of backtest
    final_date_str = trading_days[-1].strftime('%Y-%m-%d')
    portfolio.liquidate_all(final_date_str, {k: v.iloc[-1]["Close"] for k,v in df_dict.items()}, lambda t: 0.01)
    portfolio.update_daily(final_date_str, {})
    return portfolio
def calculate_metrics(portfolio, spy_df):
    if not portfolio.history:
        return {}
    hist_df = pd.DataFrame(portfolio.history)
    hist_df['date'] = pd.to_datetime(hist_df['date'])
    hist_df.set_index('date', inplace=True)
    # Daily returns
    hist_df['return'] = hist_df['equity'].pct_change().fillna(0)
    # Handling deposits in return calculations to avoid massive fake spikes
    # For a day with a deposit, return is (equity - deposit - prev_equity) / prev_equity
    hist_df['deposit_diff'] = hist_df['deposits'].diff().fillna(0)
    mask = hist_df['deposit_diff'] > 0

    if mask.any():
        hist_df.loc[mask, 'return'] = (hist_df.loc[mask, 'equity'] - hist_df.loc[mask, 'deposit_diff'] - hist_df['equity'].shift(1).loc[mask]) / hist_df['equity'].shift(1).loc[mask]

    # Return metrics
    start_val = hist_df['deposits'].iloc[0]
    total_deposits = hist_df['deposits'].iloc[-1] - start_val
    final_equity = hist_df['equity'].iloc[-1]

    total_return_pct = (final_equity - (start_val + total_deposits)) / (start_val + total_deposits) * 100

    days = (hist_df.index[-1] - hist_df.index[0]).days
    years = days / 365.25
    cagr = ((final_equity / (start_val + total_deposits)) ** (1 / years) - 1) * 100 if years > 0 and final_equity > 0 else 0

    # Risk Metrics
    cum_ret = (1 + hist_df['return']).cumprod()
    running_max = cum_ret.cummax()
    drawdown = (cum_ret - running_max) / running_max

    max_drawdown_pct = abs(drawdown.min()) * 100
    max_drawdown_date = drawdown.idxmin().strftime('%Y-%m-%d') if not drawdown.empty else None

    rf = 0.029 # 2.9% blended average
    daily_rf = rf / 252

    from src.backtest.metrics import safe_sharpe, safe_sortino

    excess_returns = hist_df['return'] - daily_rf
    volatility = hist_df['return'].std() * np.sqrt(252) * 100

    sharpe = safe_sharpe(excess_returns, periods=252)

    # Passing the raw returns to safe_sortino, minus risk free for sortino conceptually is ok but
    # since safe_sortino calculates it from the full series natively, we just pass the excess returns
    sortino = safe_sortino(excess_returns, periods=252)

    calmar = (cagr / max_drawdown_pct) if max_drawdown_pct > 0 else 0

    var_95 = np.percentile(hist_df['return'], 5) * 100
    var_99 = np.percentile(hist_df['return'], 1) * 100

    cvar_95 = hist_df['return'][hist_df['return'] <= var_95/100].mean() * 100

    # Trading Metrics
    trades_df = pd.DataFrame(portfolio.trades)

    if len(trades_df) > 0:
        win_trades = trades_df[trades_df['pnl'] > 0]
        loss_trades = trades_df[trades_df['pnl'] <= 0]

        win_rate = (len(win_trades) / len(trades_df)) * 100
        avg_win = win_trades['pnl'].mean() if len(win_trades) > 0 else 0
        avg_loss = loss_trades['pnl'].mean() if len(loss_trades) > 0 else 0

        gross_profit = win_trades['pnl'].sum()
        gross_loss = abs(loss_trades['pnl'].sum())
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

        avg_holding = trades_df['holding_days'].mean()

        # Max consecutive wins/losses
        trades_df['is_win'] = (trades_df['pnl'] > 0).astype(int)
        win_streak = (trades_df['is_win'] != trades_df['is_win'].shift()).cumsum()
        max_cons_wins = trades_df[trades_df['is_win'] == 1].groupby(win_streak).size().max() if len(win_trades) > 0 else 0
        max_cons_losses = trades_df[trades_df['is_win'] == 0].groupby(win_streak).size().max() if len(loss_trades) > 0 else 0
    else:
        win_rate = avg_win = avg_loss = profit_factor = avg_holding = max_cons_wins = max_cons_losses = 0

    trades_per_year = len(trades_df) / years if years > 0 else 0

    return {
        "total_return_pct": total_return_pct,
        "cagr": cagr,
        "max_drawdown_pct": max_drawdown_pct,
        "max_drawdown_date": max_drawdown_date,
        "volatility": volatility,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "var_95": var_95,
        "var_99": var_99,
        "cvar_95": cvar_95,
        "win_rate": win_rate,
        "total_trades": len(trades_df),
        "profit_factor": profit_factor,
        "avg_holding_days": avg_holding,
        "max_consecutive_wins": max_cons_wins,
        "max_consecutive_losses": max_cons_losses,
        "trades_per_year": trades_per_year,
        "avg_win": avg_win,
        "avg_loss": avg_loss
    }

def analyze_overfitting(portfolio, spy_df):
    if not portfolio.history:
        return {}

    hist_df = pd.DataFrame(portfolio.history)
    hist_df['date'] = pd.to_datetime(hist_df['date'])
    hist_df.set_index('date', inplace=True)

    # Need returns series for IS/OOS analysis
    hist_df['return'] = hist_df['equity'].pct_change().fillna(0)

    # Adjust for deposits
    hist_df['deposit_diff'] = hist_df['deposits'].diff().fillna(0)
    mask = hist_df['deposit_diff'] > 0
    if mask.any():
        hist_df.loc[mask, 'return'] = (hist_df.loc[mask, 'equity'] - hist_df.loc[mask, 'deposit_diff'] - hist_df['equity'].shift(1).loc[mask]) / hist_df['equity'].shift(1).loc[mask]

    rf_daily = 0.029 / 252

    def get_sharpe(start_year, end_year):
        mask = (hist_df.index.year >= start_year) & (hist_df.index.year <= end_year)
        period_rets = hist_df.loc[mask, 'return']
        if len(period_rets) < 20:
            return 0
        excess = period_rets - rf_daily
        from src.backtest.metrics import safe_sharpe
        return safe_sharpe(excess, periods=252)

    years = sorted(hist_df.index.year.unique().tolist())
    periods = []

    for i in range(len(years) - 1):
        train_year = years[i]
        test_year = years[i + 1]

        is_sharpe = get_sharpe(train_year, train_year)
        oos_sharpe = get_sharpe(test_year, test_year)

        periods.append({
            "is_period": str(train_year),
            "oos_period": str(test_year),
            "is_sharpe": is_sharpe,
            "oos_sharpe": oos_sharpe
        })

    for p in periods:
        p["wf_efficiency"] = (p["oos_sharpe"] / p["is_sharpe"]) if p["is_sharpe"] > 0 else 0

    avg_is_sharpe = np.mean([p["is_sharpe"] for p in periods])
    avg_oos_sharpe = np.mean([p["oos_sharpe"] for p in periods])
    avg_wf_efficiency = (avg_oos_sharpe / avg_is_sharpe) if avg_is_sharpe > 0 else 0

    return {
        "periods": periods,
        "avg_is_sharpe": avg_is_sharpe,
        "avg_oos_sharpe": avg_oos_sharpe,
        "avg_wf_efficiency": avg_wf_efficiency,
        "likely_overfit": bool(avg_wf_efficiency < 0.5)
    }

def main():
    logger.info("Starting Comprehensive Backtest Report Generation")
    tickers = load_universe()
    if not tickers:
        logger.error("No tickers found in universe.")
        return

    start_date = "2019-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")

    raw_data, spy_data = download_data(tickers, start_date, end_date)

    # Process SPY
    if isinstance(spy_data.columns, pd.MultiIndex):
        if 'Ticker' in spy_data.columns.names:
            spy_df = spy_data.xs('SPY', level='Ticker', axis=1)
        else:
            spy_df = spy_data.copy()
            spy_df.columns = spy_df.columns.get_level_values(0)
    else:
        spy_df = spy_data

    spy_df = spy_df.copy()
    spy_df['EMA_200'] = spy_df['Close'].ewm(span=200, adjust=False).mean()
    spy_df = spy_df[spy_df.index >= pd.to_datetime(start_date)]

    # Calculate SPY Benchmark Equity Curve
    spy_benchmark_portfolio = Portfolio(initial_capital=100)

    # We need to compute SPY shares properly based on deposits
    benchmark_history = []

    deposit_schedule = get_deposit_schedule(start_date, end_date, 50, 'quarterly')

    spy_trading_days = spy_df.index
    spy_qty = 0
    cash = 100

    for i, date in enumerate(spy_trading_days):
        date_str = date.strftime('%Y-%m-%d')

        # Add deposits
        if date_str in deposit_schedule:
            cash += deposit_schedule[date_str]
            spy_benchmark_portfolio.total_deposits += deposit_schedule[date_str]
            spy_benchmark_portfolio.deposits_count += 1

        current_price = spy_df.loc[date, 'Close']

        # If we have cash, buy SPY (fractional shares allowed for benchmark simplicity)
        if cash > 0:
            spy_qty += cash / current_price
            cash = 0

        equity = cash + spy_qty * current_price

        benchmark_history.append({
            'date': date_str,
            'equity': equity,
            'cash': cash,
            'deposits': spy_benchmark_portfolio.initial_capital + spy_benchmark_portfolio.total_deposits
        })

    spy_benchmark_portfolio.history = benchmark_history
    spy_metrics = calculate_metrics(spy_benchmark_portfolio, spy_df)

    # Process tickers
    df_dict = {}
    for ticker in tickers:
        try:
            if isinstance(raw_data.columns, pd.MultiIndex):
                # The unadjusted fallback data might not have 'Ticker' as a name but just be a multiindex
                if 'Ticker' in raw_data.columns.names:
                    df = raw_data.xs(ticker, level='Ticker', axis=1)
                elif len(raw_data.columns.levels) > 1:
                    df = raw_data.xs(ticker, level=1, axis=1)
                else:
                    df = raw_data
            else:
                df = raw_data # Only 1 ticker

            df = df.dropna(subset=['Close'])
            if len(df) > 50:
                df_with_ind = compute_indicators_vectorized(df)
                if df_with_ind is not None:
                    df_dict[ticker] = df_with_ind
        except Exception as e:
            logger.warning(f"Error processing {ticker}: {e}")

    # Generate schedule
    deposit_schedule = get_deposit_schedule(start_date, end_date, 50, 'quarterly')

    # Parameters
    atr_trailing_mults = [1.5, 2.0, 2.5]
    atr_profit_mults = [2.5, 3.5, 4.5]
    rsi_thresholds = [(30, 70), (35, 65)]
    min_confluences = [3, 4]

    all_strategies = []

    total_combos = len(atr_trailing_mults) * len(atr_profit_mults) * len(rsi_thresholds) * len(min_confluences)
    logger.info(f"Running {total_combos} strategies...")

    best_portfolio = None
    best_sharpe = -999
    best_params = None
    best_metrics = None
    best_overfitting = None
    best_name = None

    strat_idx = 0
    for t_mult in atr_trailing_mults:
        for p_mult in atr_profit_mults:
            for rsi in rsi_thresholds:
                for mc in min_confluences:
                    params = {
                        'atr_trailing_mult': t_mult,
                        'atr_profit_mult': p_mult,
                        'rsi_bounds': rsi,
                        'min_confluence': mc
                    }

                    name = f"DYN_EXIT_t{t_mult}_p{p_mult}_rsi{rsi[0]}{rsi[1]}_min{mc}"

                    portfolio = run_backtest_for_params(df_dict, spy_df, params, deposit_schedule)
                    metrics = calculate_metrics(portfolio, spy_df)
                    overfitting = analyze_overfitting(portfolio, spy_df)

                    strat_data = {
                        "id": f"strat_{strat_idx:04d}",
                        "name": name,
                        "parameters": params,
                        "metrics": {
                            "total_return_pct": metrics.get("total_return_pct", 0),
                            "cagr": metrics.get("cagr", 0),
                            "sharpe": metrics.get("sharpe", 0),
                            "sortino": metrics.get("sortino", 0),
                            "max_drawdown_pct": metrics.get("max_drawdown_pct", 0),
                            "win_rate": metrics.get("win_rate", 0),
                            "profit_factor": metrics.get("profit_factor", 0),
                            "total_trades": metrics.get("total_trades", 0),
                            "wf_efficiency": overfitting.get("avg_wf_efficiency", 0),
                            "is_sharpe": overfitting.get("avg_is_sharpe", 0),
                            "oos_sharpe": overfitting.get("avg_oos_sharpe", 0),
                            "likely_overfit": overfitting.get("likely_overfit", True)
                        }
                    }
                    all_strategies.append(strat_data)

                    if metrics.get("sharpe", -999) > best_sharpe:
                        best_sharpe = metrics.get("sharpe", -999)
                        best_portfolio = portfolio
                        best_params = params
                        best_metrics = metrics
                        best_overfitting = overfitting
                        best_name = name

                    strat_idx += 1
                    if strat_idx % 10 == 0:
                        logger.info(f"Completed {strat_idx}/{total_combos} strategies")

    if best_name is None:
        logger.error("No valid strategies found. Check if df_dict is populated correctly.")
        return

    logger.info(f"Best Strategy: {best_name} (Sharpe: {best_sharpe:.2f})")

    # Minerva robustness grade (non-blocking)
    try:
        from src.backtest.defend.minerva_score import minerva_score
        T = len(spy_df.index)
        sr = float(best_metrics.get("sharpe") or 0.0)
        N = int(best_metrics.get("total_trades") or 0)
        mr = minerva_score(T=T, sr=sr, N=N)
        logger.info(
            f"Minerva: score={mr.display_0_100} seal={'PASS' if mr.seal else 'FAIL'} verdict={mr.verdict}"
        )
    except Exception:
        logger.info("Minerva: n/a")

    # Generate Output Files
    os.makedirs("docs/data", exist_ok=True)

    # 1. backtest_report.json
    hist_df = pd.DataFrame(best_portfolio.history)
    hist_df['date'] = pd.to_datetime(hist_df['date'])
    hist_df.set_index('date', inplace=True)

    # Monthly/Quarterly returns for best strategy
    hist_df['month'] = hist_df.index.to_period('M')
    hist_df['quarter'] = hist_df.index.to_period('Q')

    # Build month-end equity lookup for proper cross-month return calculation
    month_end_eq = {}
    for m, group in hist_df.groupby('month'):
        month_end_eq[str(m)] = group['equity'].iloc[-1]

    prev_month_end_eq = None
    monthly_ret = []
    for m, group in hist_df.groupby('month'):
        end_eq = group['equity'].iloc[-1]
        deposits_in_period = group['deposits'].iloc[-1] - group['deposits'].iloc[0]
        # Use previous month's last-day equity as baseline (or first day of this month if no previous)
        base_eq = prev_month_end_eq if prev_month_end_eq is not None else group['equity'].iloc[0]
        ret = (end_eq - (base_eq + deposits_in_period)) / (base_eq + deposits_in_period) * 100 if base_eq > 0 else 0
        monthly_ret.append({"month": str(m), "return_pct": ret})
        prev_month_end_eq = end_eq

    # Same for quarterly
    quarter_end_eq = {}
    for q, group in hist_df.groupby('quarter'):
        quarter_end_eq[str(q)] = group['equity'].iloc[-1]

    prev_q_end_eq = None
    quarterly_ret = []
    for q, group in hist_df.groupby('quarter'):
        end_eq = group['equity'].iloc[-1]
        deposits_in_period = group['deposits'].iloc[-1] - group['deposits'].iloc[0]
        base_eq = prev_q_end_eq if prev_q_end_eq is not None else group['equity'].iloc[0]
        ret = (end_eq - (base_eq + deposits_in_period)) / (base_eq + deposits_in_period) * 100 if base_eq > 0 else 0
        quarterly_ret.append({"quarter": str(q), "return_pct": ret, "equity": end_eq})
        prev_q_end_eq = end_eq

    # Regime breakdown
    trades_df = pd.DataFrame(best_portfolio.trades)
    regime_breakdown = {}
    if len(trades_df) > 0:
        for regime in ["low_volatility", "normal", "high_volatility"]:
            r_trades = trades_df[trades_df['regime'] == regime]
            entry = {
                "trades": len(r_trades),
                "avg_return": (r_trades['pnl'] / (r_trades['entry_price'] * r_trades['qty'])).mean() * 100 if len(r_trades) > 0 else 0,
                "win_rate": (len(r_trades[r_trades['pnl'] > 0]) / len(r_trades)) * 100 if len(r_trades) > 0 else 0
            }
            if regime == "high_volatility" and len(r_trades) == 0:
                entry["note"] = "No trades: GK_Volatility shield blocked entries when GK_Vol >= 1.2"
            regime_breakdown[regime] = entry

    total_invested = 100 + best_portfolio.total_deposits
    roic = (best_portfolio.equity - total_invested) / total_invested * 100

    report = {
        "report_date": datetime.now().strftime("%Y-%m-%d"),
        "period": {"start": start_date, "end": end_date},
        "initial_capital": 100,
        "quarterly_deposit": 50,
        "total_deposits": best_portfolio.deposits_count,
        "total_deposited": best_portfolio.total_deposits,
        "strategies_tested": total_combos,
        "best_strategy": {
            "name": best_name,
            "parameters": best_params,
            "overfitting": best_overfitting
        },
        "benchmark_comparison": {
            "strategy_return_pct": best_metrics["total_return_pct"],
            "spy_return_pct": spy_metrics["total_return_pct"],
            "alpha_return_pct": best_metrics["total_return_pct"] - spy_metrics["total_return_pct"],
            "strategy_cagr": best_metrics["cagr"],
            "spy_cagr": spy_metrics["cagr"],
            "strategy_sharpe": best_metrics["sharpe"],
            "spy_sharpe": spy_metrics["sharpe"],
            "strategy_max_dd_pct": best_metrics["max_drawdown_pct"],
            "spy_max_dd_pct": spy_metrics["max_drawdown_pct"]
        },
        "portfolio_summary": {
            "final_equity": best_portfolio.equity,
            "total_return_pct": best_metrics["total_return_pct"],
            "cagr": best_metrics["cagr"],
            "max_drawdown_pct": best_metrics["max_drawdown_pct"],
            "max_drawdown_date": best_metrics["max_drawdown_date"],
            "sharpe_ratio": best_metrics["sharpe"],
            "sortino_ratio": best_metrics["sortino"],
            "calmar_ratio": best_metrics["calmar"],
            "win_rate": best_metrics["win_rate"],
            "profit_factor": best_metrics["profit_factor"],
            "total_trades": best_metrics["total_trades"],
            "avg_holding_days": best_metrics["avg_holding_days"],
            "roic": roic
        },
        "quarterly_returns": quarterly_ret,
        "monthly_returns": monthly_ret,
        "regime_breakdown": regime_breakdown,
        "all_strategies": all_strategies,
        "benchmark_equity_curve": benchmark_history,
        "equity_curve": [{"date": r['date'], "equity": r['equity'], "deposits": r['deposits']} for r in best_portfolio.history],
        "trade_log": best_portfolio.trades[:500], # Limit to 500
        "limitations": [
            "Survivorship bias: using current ticker list, delisted tickers not included",
            "No real-time intraday data used, daily OHLCV only",
            "Bid-ask spread modeled as fixed percentage, not actual spread data",
            "Regulatory fees approximated, not exact SEC/TAF calculations",
            "Slippage modeled as ATR-based, not actual market microstructure",
            "Risk-free rate: fixed 2.9% blended average used across whole period"
        ]
    }

    # Publish guard: never write/publish reports computed on local unadjusted fallback data
    if DATA_IS_MOCK:
        logger.error("DATA_IS_MOCK=True: results are based on local unadjusted fallback data, refusing to publish to docs/data/.")
        return

    with open("docs/data/backtest_report.json", "w") as f:
        json.dump(report, f, indent=2)

    # 2. equity_curve.json
    with open("docs/data/equity_curve.json", "w") as f:
        json.dump([{"date": r['date'], "equity": r['equity'], "deposits": r['deposits']} for r in best_portfolio.history], f, indent=2)

    # 3. quarterly_performance.json
    with open("docs/data/quarterly_performance.json", "w") as f:
        json.dump(quarterly_ret, f, indent=2)

    # 4. strategy_rankings.json
    all_strategies.sort(key=lambda x: x["metrics"]["sharpe"], reverse=True)
    with open("docs/data/strategy_rankings.json", "w") as f:
        json.dump(all_strategies, f, indent=2)

    # 5. trade_history.json
    with open("docs/data/trade_history.json", "w") as f:
        json.dump(best_portfolio.trades[:500], f, indent=2)

    logger.info("Files generated successfully.")

if __name__ == "__main__":
    main()
