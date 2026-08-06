import math
from typing import Dict, Optional, List

import pandas as pd
import numpy as np

from nautilus_trader.trading.strategy import Strategy, StrategyConfig
from nautilus_trader.model.data import Bar
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.enums import OrderSide, TimeInForce

# Using indicators available in nautilus_trader
from nautilus_trader.indicators import AverageTrueRange
from nautilus_trader.indicators import BollingerBands
from nautilus_trader.indicators import ExponentialMovingAverage
from nautilus_trader.indicators import RateOfChange
from nautilus_trader.indicators import RelativeStrengthIndex

class WSBConfluenceStrategyConfig(StrategyConfig):
    spy_instrument_id: InstrumentId
    atr_stop_multiplier: float = 2.0
    atr_target_multiplier: float = 3.0
    max_positions: int = 4
    risk_per_trade: float = 0.02
    max_capital_per_position: float = 0.25
    max_hold_days: int = 30

class WSBConfluenceStrategy(Strategy):
    def __init__(self, config: WSBConfluenceStrategyConfig):
        super().__init__(config)
        self.spy_instrument_id = config.spy_instrument_id

        # Indicator dictionaries keyed by InstrumentId
        self.ema_20: Dict[InstrumentId, ExponentialMovingAverage] = {}
        self.rsi_14: Dict[InstrumentId, RelativeStrengthIndex] = {}
        self.bb_20_2: Dict[InstrumentId, BollingerBands] = {}
        self.atr_14: Dict[InstrumentId, AverageTrueRange] = {}
        self.roc_60: Dict[InstrumentId, RateOfChange] = {}

        # SPY 200 EMA
        self.spy_ema_200: Optional[ExponentialMovingAverage] = None
        self.spy_close_under_ema = False

        # Additional state tracking
        # To compute Garman-Klass volatility, we need last N days of data.
        self.history_bars: Dict[InstrumentId, List[Bar]] = {}

        # To compute Heikin-Ashi, we need the previous HA bar
        self.ha_state: Dict[InstrumentId, dict] = {}

        # Signals mapped to ROC to process at end of bar updates (or whenever)
        self.active_signals: Dict[InstrumentId, float] = {}
        self.position_state = {}

    def on_start(self):
        # We need to initialize indicators for all subscribed instruments
        # We can do this as instruments are added or in on_start if we know them
        pass

    def on_instrument_initialized(self, instrument: Instrument):
        instrument_id = instrument.id

        # Derive bar_type manually or assume a specific BarType
        from nautilus_trader.model.data import BarType
        bar_type = BarType.from_str(f"{instrument_id}-1-DAY-LAST-EXTERNAL")
        if instrument_id == self.spy_instrument_id:
            self.spy_ema_200 = ExponentialMovingAverage(200)
            self.register_indicator_for_bars(bar_type, self.spy_ema_200)
        else:
            self.ema_20[instrument_id] = ExponentialMovingAverage(20)
            self.rsi_14[instrument_id] = RelativeStrengthIndex(14)
            self.bb_20_2[instrument_id] = BollingerBands(20, 2.0)
            self.atr_14[instrument_id] = AverageTrueRange(14)
            self.roc_60[instrument_id] = RateOfChange(60)

            self.register_indicator_for_bars(bar_type, self.ema_20[instrument_id])
            self.register_indicator_for_bars(bar_type, self.rsi_14[instrument_id])
            self.register_indicator_for_bars(bar_type, self.bb_20_2[instrument_id])
            self.register_indicator_for_bars(bar_type, self.atr_14[instrument_id])
            self.register_indicator_for_bars(bar_type, self.roc_60[instrument_id])

            self.history_bars[instrument_id] = []
            self.ha_state[instrument_id] = None

    def on_bar(self, bar: Bar):
        instrument_id = bar.bar_type.instrument_id

        # 1. SPY 200 EMA Suppression
        if instrument_id == self.spy_instrument_id:
            if self.spy_ema_200.initialized:
                spy_ema_val = self.spy_ema_200.value
                self.spy_close_under_ema = float(bar.close) < spy_ema_val
            return # Don't trade SPY itself

        # 2. Update state for Heikin-Ashi and GK Vol
        close_price = float(bar.close)
        open_price = float(bar.open)
        high_price = float(bar.high)
        low_price = float(bar.low)

        self.history_bars[instrument_id].append(bar)
        if len(self.history_bars[instrument_id]) > 20:
            self.history_bars[instrument_id].pop(0)

        # Heikin-Ashi calculation
        if self.ha_state[instrument_id] is None:
            ha_open = open_price
            ha_close = (open_price + high_price + low_price + close_price) / 4.0
        else:
            prev_ha = self.ha_state[instrument_id]
            ha_open = (prev_ha['open'] + prev_ha['close']) / 2.0
            ha_close = (open_price + high_price + low_price + close_price) / 4.0

        self.ha_state[instrument_id] = {'open': ha_open, 'close': ha_close}

        # Check if indicators are ready
        if not (self.ema_20[instrument_id].initialized and
                self.rsi_14[instrument_id].initialized and
                self.bb_20_2[instrument_id].initialized and
                self.atr_14[instrument_id].initialized and
                self.roc_60[instrument_id].initialized):
            return

        # GK Volatility calculation
        # Garman-Klass Volatility = sqrt(252 * (1/N) * sum( 0.5*[log(H/L)]^2 - (2*log2 - 1)*[log(C/O)]^2 ))
        # We will use N=20 (from history_bars)
        gk_vol = 0.0
        if len(self.history_bars[instrument_id]) == 20:
            sum_gk = 0.0
            for b in self.history_bars[instrument_id]:
                h = float(b.high)
                l = float(b.low)
                c = float(b.close)
                o = float(b.open)
                term1 = 0.5 * (math.log(h / l) ** 2)
                term2 = (2 * math.log(2) - 1) * (math.log(c / o) ** 2)
                sum_gk += max(0, term1 - term2) # Ensure non-negative
            gk_vol = math.sqrt(252.0 * (sum_gk / 20.0))

        # 3. Confluence Score
        score = 0
        if ha_close > ha_open:
            score += 1
        if close_price > self.ema_20[instrument_id].value:
            score += 1
        if 35 <= self.rsi_14[instrument_id].value <= 65:
            score += 1
        if close_price > self.bb_20_2[instrument_id].lower_band:
            score += 1
        if gk_vol < 1.0:
            score += 1

        # Fire when score >= 4
        if score >= 4:
            self.active_signals[instrument_id] = self.roc_60[instrument_id].value

        # Note: Since this is an event-driven system, and we receive bars sequentially,
        # ranking by ROC(60) across all instruments natively requires synchronizing.
        # However, to meet the requirements "Rank active-signal tickers by 60-day ROC and fill up to 4 positions",
        # we can process active signals here or wait until a scheduling method.
        # The prompt says: "Rank active-signal tickers by 60-day ROC and fill up to 4 positions."
        # We'll evaluate entries and exits on every bar or schedule a timer. Let's do it in a simplistic way:
        # we process active signals right after updating, or we maintain a list and check positions.

        self.manage_exits(instrument_id, bar)
        self.process_entries()

    def process_entries(self):
        if self.spy_close_under_ema:
            self.active_signals.clear()
            return

        current_positions = len(self.portfolio.positions())
        available_slots = self.config.max_positions - current_positions

        if available_slots <= 0 or not self.active_signals:
            return

        # Sort active signals by ROC descending
        sorted_signals = sorted(self.active_signals.items(), key=lambda x: x[1], reverse=True)

        filled_slots = 0
        for instrument_id, roc_val in sorted_signals:
            if filled_slots >= available_slots:
                break
            if self.portfolio.has_position(instrument_id):
                continue
            filled_slots += 1

            instrument = self.cache.instrument(instrument_id)
            if not instrument:
                continue

            last_bar = self.cache.bar(instrument_id)
            if not last_bar:
                continue

            close_price = float(last_bar.close)
            atr_val = self.atr_14[instrument_id].value
            if atr_val <= 0:
                continue

            equity = float(self.portfolio.margin_balance())

            # Risk Parity Sizing: shares = (equity * 0.02) / (atr_stop_multiplier * ATR_14)
            risk_amount = equity * self.config.risk_per_trade
            stop_distance = self.config.atr_stop_multiplier * atr_val
            shares = math.floor(risk_amount / stop_distance)

            # Cap at 25% of equity
            max_shares = math.floor((equity * self.config.max_capital_per_position) / close_price)
            shares = min(shares, max_shares)

            if shares > 0:
                order = self.order_factory.market(
                    instrument_id=instrument_id,
                    order_side=OrderSide.BUY,
                    quantity=instrument.make_qty(shares)
                )

                # Dynamic exits logic setup
                stop_loss = close_price - stop_distance
                take_profit = close_price + (self.config.atr_target_multiplier * atr_val)

                # Tag the order with our custom exits
                order.tags = {
                    'stop_loss': str(stop_loss),
                    'take_profit': str(take_profit),
                    'entry_time': str(last_bar.ts_init),
                    'atr_stop_mult': str(self.config.atr_stop_multiplier),
                    'atr_val': str(atr_val)
                }
                self.submit_order(order)

        self.active_signals.clear()

    def manage_exits(self, instrument_id: InstrumentId, bar: Bar):
        position = self.portfolio.position(instrument_id)
        if not position:
            return

        close_price = float(bar.close)

        # We need the tags from the entry order to manage exits.
        # Nautilus doesn't directly store tags on positions, so we look at the orders that filled it
        # Or we can just maintain a local dict of position state.

        # Initialize state for new position
        if instrument_id not in self.position_state:
            atr_val = self.atr_14[instrument_id].value
            entry_price = float(position.avg_px)
            stop_dist = self.config.atr_stop_multiplier * atr_val
            self.position_state[instrument_id] = {
                'stop_loss': entry_price - stop_dist,
                'take_profit': entry_price + (self.config.atr_target_multiplier * atr_val),
                'entry_time': bar.ts_init,
                'entry_price': entry_price
            }

        state = self.position_state[instrument_id]

        # Trailing stop logic: moves up only
        # The prompt says: "trailing ATR stop (moves up only)"
        # So stop_loss is max(current_stop_loss, close_price - atr_stop_multiplier * ATR_14)
        atr_val = self.atr_14[instrument_id].value
        new_stop = close_price - (self.config.atr_stop_multiplier * atr_val)
        if new_stop > state['stop_loss']:
            state['stop_loss'] = new_stop

        # Check exits
        exit_reason = None
        if close_price <= state['stop_loss']:
            exit_reason = 'stop_loss'
        elif close_price >= state['take_profit']:
            exit_reason = 'take_profit'
        else:
            # 30-day max-hold close
            # Time diff in nanoseconds
            days_held = (bar.ts_init - state['entry_time']) / (1e9 * 60 * 60 * 24)
            if days_held >= self.config.max_hold_days:
                exit_reason = 'max_hold'

        if exit_reason:
            self.close_position(instrument_id)
            del self.position_state[instrument_id]

    def close_position(self, instrument_id: InstrumentId):
        position = self.portfolio.position(instrument_id)
        if position:
            instrument = self.cache.instrument(instrument_id)
            if instrument:
                order = self.order_factory.market(
                    instrument_id=instrument_id,
                    order_side=OrderSide.SELL if position.is_long else OrderSide.BUY,
                    quantity=position.quantity
                )
                self.submit_order(order)
