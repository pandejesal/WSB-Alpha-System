# ============================================================================
# PHASE 4: LIVE CAPITAL GATE & SAFETY RAILS
# ============================================================================

# This flag controls live trading explicitly.
# It MUST be manually flipped to True by the repo owner after sufficient paper trading evidence.
LIVE_TRADING_ENABLED = False

# Hard-coded safety rails for $50-$100 small account sizes
# The self-improvement loop is explicitly forbidden from modifying these values.

# Maximum percentage of account allocated to a single position (e.g., 20% limits to ~5 positions max)
MAX_POSITION_SIZE_PCT = 0.20

# Absolute maximum concurrent positions
MAX_CONCURRENT_POSITIONS = 4

# Circuit breakers (Halt trading if drawdown exceeds these thresholds)
DAILY_LOSS_CIRCUIT_BREAKER_PCT = 0.05   # Halt if account drops > 5% in a single day
WEEKLY_LOSS_CIRCUIT_BREAKER_PCT = 0.10  # Halt if account drops > 10% in a week
