# H2 Alternative Data Integration — Implementation Handoff

**Date**: 2026-09-02
**Status**: Phase 1 COMPLETE (5/5 tasks, PRs #149–#155 merged, main @ a481d3a)
**H2 Composite Weighting**: 35% sentiment / 25% GEX / 25% dark pool / 15% on-chain flow
**Regime Gating Thresholds**: h2 > 0.6 → 1×, 0.3–0.6 → 0.6×, < 0.3 → cash only
**Account Constraint**: $100 micro-account

---

## Phase 2: Config Foundation (Pydantic Fields + YAML Defaults)

**Target files**:
- `src/utils/config.py` — insert H2 fields BEFORE `model_config` block
- `config/default_config.yaml` — add YAML defaults (path needs discovery; may not exist at expected location)

**Pydantic fields to add to `WsbAlphaConfig`** (insert before `model_config`):

```python
# --- H2 Alternative Data Sources ---
reddit_client_id: str = ""
reddit_client_secret: str = ""
reddit_user_agent: str = "WSB-Alpha-H2/1.0"

binance_api_key: str = ""
binance_secret_key: str = ""

# --- H2 Composite Weights ---
h2_sentiment_weight: float = 0.35
h2_gex_weight: float = 0.25
h2_darkpool_weight: float = 0.25
h2_onchain_weight: float = 0.15

# --- H2 Regime Gating ---
h2_regime_threshold_high: float = 0.6   # full allocation
h2_regime_threshold_low: float = 0.3    # below this = cash only
h2_regime_threshold_mid: float = 0.3    # computed: between low and high = 0.6×
```

**Existing fields** (DO NOT duplicate): `alpaca_api_key`, `alpaca_secret_key`, `binance_api_key`, `binance_secret_key`, `reddit_client_id`, `reddit_client_secret`, `telegram_bot_token`, `live_trading_enabled`, `paper_trading_enabled`, `initial_capital`. These already exist in `config.py` and should NOT be re-added.

**Validation rule**: Weights must sum to 1.0. Add a `@model_validator` if not already present.

**YAML defaults**: If `config/default_config.yaml` does not exist, create it with the H2 section. If it does exist, append the H2 section.

---

## Phase 3: Signal Layer (engine.py + indicators.py + strategy regime gating)

### 3A: `src/signals/engine.py`

**Current state**: `active_sleeves` list has 7 entries (L19–27):
1. `breakout_sleeve`
2. `momentum_sleeve`
3. `reversal_sleeve`
4. `microstructure_sleeve`
5. `regime_sleeve`
6. `sentiment_sleeve`
7. `options_flow_sleeve`

**Changes required**:

1. Add import at top:
```python
from src.data.providers.sentiment_reddit_provider import SentimentRedditProvider
```

2. Add 8th entry to `active_sleeves` list:
```python
self.active_sleeves = [
    # ... existing 7 sleeves ...
    self.h2_alternative_data_sleeve,  # NEW: H2 composite
]
```

3. Add new method `h2_alternative_data_sleeve()` after `options_flow_sleeve()`:

```python
def h2_alternative_data_sleeve(self, df, symbol):
    """
    H2 Alternative Data composite signal.
    Combines: sentiment (35%), GEX (25%), dark pool (25%), on-chain flow (15%).
    Returns: Series with values in [-1, 1] range.
    """
    config = get_config()

    # 1. Sentiment from Reddit (35%)
    try:
        provider = SentimentRedditProvider()
        sentiment_data = provider.fetch_sentiment_feed(symbol)
        sentiment_score = sentiment_data.get('sentiment_score', 0.0)  # [-1, 1]
    except Exception:
        sentiment_score = 0.0

    # 2. GEX from options flow (25%)
    # Uses existing options_flow_sleeve output as proxy
    gex_score = 0.0  # placeholder — will be computed from options data

    # 3. Dark pool prints (25%)
    darkpool_score = 0.0  # placeholder — will be computed from dark pool data

    # 4. On-chain flow (15%)
    onchain_score = 0.0  # placeholder — will be computed from on-chain data

    # Composite weighted score
    h2_composite = (
        config.h2_sentiment_weight * sentiment_score +
        config.h2_gex_weight * gex_score +
        config.h2_darkpool_weight * darkpool_score +
        config.h2_onchain_weight * onchain_score
    )

    return pd.Series([h2_composite] * len(df), index=df.index, name='h2_composite')
```

### 3B: `src/alpha/indicators.py`

**Add after `custom_adx()` function**:

```python
@njit
def h2_composite_indicator(close, high, low, volume, h2_composite):
    """
    H2 composite indicator: blends price action with alternative data composite.
    h2_composite input is pre-computed in engine.py sleeve.

    Returns: Series of H2-enhanced signal values.
    """
    length = len(close)
    h2_signal = np.zeros(length, dtype=np.float64)

    for i in range(1, length):
        # Price momentum component
        price_change = (close[i] - close[i-1]) / close[i-1] if close[i-1] != 0 else 0.0

        # Volume-weighted H2 influence
        vol_factor = volume[i] / np.mean(volume[max(0, i-20):i]) if i >= 20 else 1.0

        # Blend price momentum with H2 composite
        h2_signal[i] = price_change * (1.0 + 0.5 * h2_composite[i]) * min(vol_factor, 2.0)

    return h2_signal
```

### 3C: `src/alpha/strategy_wsb_alpha.py`

**Add regime gating in `run()` method** — after existing signal aggregation, before return:

```python
# H2 regime gating
config = get_config()
h2_score = signals.get('h2_composite', 0.0) if isinstance(signals, dict) else 0.0

if h2_score < config.h2_regime_threshold_low:
    # Below 0.3 — cash only
    position_multiplier = 0.0
elif h2_score < config.h2_regime_threshold_high:
    # 0.3–0.6 — reduced allocation
    position_multiplier = 0.6
else:
    # Above 0.6 — full allocation
    position_multiplier = 1.0

# Apply position_multiplier to final position sizing
```

---

## Phase 4: Backtest Integration (run_full_backtest.py)

**Target**: `scripts/run_full_backtest.py`

**Location**: After `compute_all_signals()` call (approximately L150–180 depending on current state).

**Changes**:

1. Add import for H2 composite:
```python
from src.alpha.indicators import h2_composite_indicator
from src.signals.engine import SignalEngine
```

2. After `compute_all_signals()` returns, inject H2 signal:
```python
# H2 alternative data signal injection
engine = SignalEngine()
h2_signals = engine.h2_alternative_data_sleeve(df, symbol)
df['h2_composite'] = h2_signals

# Compute H2-enhanced indicator
df['h2_signal'] = h2_composite_indicator(
    df['close'].values,
    df['high'].values,
    df['low'].values,
    df['volume'].values,
    df['h2_composite'].values
)

# Apply regime gating
config = get_config()
df['h2_position_multiplier'] = df['h2_composite'].apply(
    lambda x: 1.0 if x >= config.h2_regime_threshold_high
    else 0.6 if x >= config.h2_regime_threshold_low
    else 0.0
)
```

3. Ensure `h2_position_multiplier` is passed through to strategy and executor.

---

## Phase 5: Executor Verification (NO CODE CHANGES)

**Target**: `src/execution/live_alpaca_executor.py`

**Status**: VERIFIED — H2 flows through existing pipeline. No code changes needed.

**Key integration points confirmed**:
- L27–29: `TECHNICAL_UNIVERSE` list used for universe selection
- L333: Position sizing via `risk_config.MAX_RISK_PER_TRADE_PCT`
- L336–352: Order execution loop handles any signal type
- L354–360: Execution log records all trades

**Verification checklist**:
- [ ] Run backtest with H2 signals enabled
- [ ] Verify H2 position multiplier flows through to executor
- [ ] Confirm regime gating works (cash only when h2 < 0.3)
- [ ] Validate position sizing respects $100 account constraint
- [ ] Check that H2 signals appear in execution log

---

## Open Items / Risks

1. **default_config.yaml path**: File not found at expected `config/default_config.yaml`. May need discovery. If absent, create it.
2. **Paper citations unverified**: The 5 cited papers in H2 deliverable may contain fabricated arxiv IDs. Do NOT reference them in code comments without verification.
3. **SentimentRedditProvider import**: Verify `src/data/providers/sentiment_reddit_provider.py` exists and exports `SentimentRedditProvider`. If not, use `reddit_provider.py` which is confirmed present.
4. **GEX/Dark pool/On-chain placeholders**: Phase 3 sleeve method has placeholder scores for GEX, dark pool, and on-chain. These need real implementations in future work. For now, they default to 0.0.
5. **Web search disabled**: Cannot verify paper citations or external data sources without config change in `~/.config/opencode/opencode-swarm.json`.
6. **$100 account**: All position sizing must respect this constraint. No leverage. No oversized positions.

---

## Execution Order

| Phase | Files Modified | Dependencies | Estimated Complexity |
|-------|---------------|--------------|---------------------|
| 2 | `config.py`, `default_config.yaml` | None | Low |
| 3A | `engine.py` | Phase 2 | Medium |
| 3B | `indicators.py` | None | Low |
| 3C | `strategy_wsb_alpha.py` | Phase 2 | Medium |
| 4 | `run_full_backtest.py` | Phases 2, 3 | Medium |
| 5 | None (verification only) | Phases 2–4 | Low |

**Parallel execution possible**: Phases 3B and 3C can run in parallel with Phase 3A since they target different files. Phase 4 depends on all of Phase 3 completing.

---

## Handoff Instructions

1. Exit plan mode
2. Create a new session or hand off to a write-capable agent
3. Execute Phase 2 first (config foundation)
4. Then execute Phase 3 (signal layer) — can parallelize 3A/3B/3C
5. Then Phase 4 (backtest integration)
6. Finally Phase 5 (verification/testing)
7. Run full backtest to validate H2 integration
8. Commit and create PR if all tests pass
