# ============================================================================
# PHASE 4: LIVE CAPITAL GATE & SAFETY RAILS
# ============================================================================

# This flag controls live trading explicitly.
# It MUST be manually flipped to True by the repo owner after sufficient paper trading evidence.
LIVE_TRADING_ENABLED = False

# Hard-coded safety rails for dynamic compounding ($100 to $500 target)
# The self-improvement loop is explicitly forbidden from modifying these values.

# Dynamic risk model: % of equity to risk per trade.
# Replaces the flat $1.00 risk to allow compounding.
RISK_PER_TRADE_PCT = 0.03 # 3% risk per trade

# Maximum percentage of account allocated to a single position
# Increased slightly to allow sizing up with dynamic conviction multipliers
MAX_POSITION_SIZE_PCT = 0.25

# Absolute maximum concurrent positions
MAX_CONCURRENT_POSITIONS = 4

# Circuit breakers (Halt trading if drawdown exceeds these thresholds)
# Scaled slightly to accommodate aggressive growth compounding
DAILY_LOSS_CIRCUIT_BREAKER_PCT = 0.08   # Halt if account drops > 8% in a single day
WEEKLY_LOSS_CIRCUIT_BREAKER_PCT = 0.15  # Halt if account drops > 15% in a week
