LIVE_TRADING_ENABLED = False
RISK_PER_TRADE_PCT = 0.03
MAX_POSITION_SIZE_PCT = 0.25
MAX_CONCURRENT_POSITIONS = 4
# NOTE: These limits are conservative for paper trading.
# Consider adjusting to 10% daily / 20% weekly after initial validation.
DAILY_LOSS_CIRCUIT_BREAKER_PCT = 0.08
WEEKLY_LOSS_CIRCUIT_BREAKER_PCT = 0.15