# Canonical risk caps — single source (CS-04)
# CH-07 intentional E402: caps defined before re-export imports — do not move imports
# above caps; this ordering is intentional to keep single-source caps at top and
# avoid circular dependency with src.risk.position_sizing. Deviation documented.
MAX_NOTIONAL_LEV = 1.0
HALF_KELLY = 0.5
BASE_RISK_PCT = 0.02
MAX_POSITION_PCT = 0.20  # also exported as MAX_POSITION_SIZE_PCT alias

from src.risk.position_sizing import (
    ACCOUNT_BASE_CAPITAL,
    DAILY_LOSS_CIRCUIT_BREAKER_PCT,
    LIVE_TRADING_ENABLED,
    MAX_CONCURRENT_POSITIONS,
    MAX_DRAWDOWN_CIRCUIT_BREAKER_PCT,
    MAX_POSITION_SIZE_PCT,
    MAX_RISK_PER_TRADE_PCT,
    WEEKLY_LOSS_CIRCUIT_BREAKER_PCT,
)

# W5 cost model realism — per-asset tiers (docs/GATESPEC38_TRACKS.md §1, docs/OPTIMIZATION_PLAYBOOK.md)
# Equities (SPY / UNI): 5-7bps slippage + 1bp commission, vol-scaled
# BTC (btc_vol/btc_donchian/btc_regime): 15-25bps slippage + 1bp commission, vol-scaled
# vol_scalar = rolling_std(20) / median_60 ; cost = base + commission + (vol_scalar-1).clip(0)*scale
# fallback 5bps never 0 (fail-closed)
EQUITY_SLIPPAGE_BPS = 5.0
EQUITY_SLIPPAGE_MAX_BPS = 7.0
EQUITY_COMMISSION_BPS = 1.0
BTC_SLIPPAGE_BPS = 15.0
BTC_SLIPPAGE_MAX_BPS = 25.0
BTC_COMMISSION_BPS = 1.0
BORROW_COST_BPS = 10.0  # 0.1% borrow guard if short (not used now, fail-closed guard)
COST_FALLBACK_BPS = 5.0
VOL_WINDOW = 20
VOL_MEDIAN_WINDOW = 60