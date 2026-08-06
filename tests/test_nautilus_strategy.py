
import pytest
import math
from unittest.mock import MagicMock, patch

import pandas as pd
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.test_kit.providers import TestInstrumentProvider
from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.objects import Price, Quantity

from src.backtest.engines.nautilus_strategy import WSBConfluenceStrategy, WSBConfluenceStrategyConfig

@pytest.fixture
def test_setup():
    spy_instr = TestInstrumentProvider.equity(symbol="SPY", venue="TEST")
    aapl_instr = TestInstrumentProvider.equity(symbol="AAPL", venue="TEST")

    spy_id = spy_instr.id
    aapl_id = aapl_instr.id

    config = WSBConfluenceStrategyConfig(
        spy_instrument_id=spy_id,
        atr_stop_multiplier=2.0,
        atr_target_multiplier=3.0,
        max_positions=4,
        risk_per_trade=0.02,
        max_capital_per_position=0.25,
        max_hold_days=30
    )

    strategy = WSBConfluenceStrategy(config)

    strategy.on_instrument_initialized(spy_instr)
    strategy.on_instrument_initialized(aapl_instr)

    return strategy, spy_instr, aapl_instr

def create_bar(instrument_id: InstrumentId, dt_str: str, open_p: float, high_p: float, low_p: float, close_p: float):
    dt = pd.Timestamp(dt_str, tz="UTC")
    ts = dt_to_unix_nanos(dt)
    bar_type = BarType.from_str(f"{instrument_id}-1-DAY-LAST-EXTERNAL")
    return Bar(
        bar_type=bar_type,
        open=Price.from_str(str(open_p)),
        high=Price.from_str(str(high_p)),
        low=Price.from_str(str(low_p)),
        close=Price.from_str(str(close_p)),
        volume=Quantity.from_int(1000),
        ts_event=ts,
        ts_init=ts
    )

def test_indicator_init(test_setup):
    strategy, spy_instr, aapl_instr = test_setup

    assert not strategy.spy_ema_200.initialized
    assert not strategy.ema_20[aapl_instr.id].initialized

def test_spy_ema_suppression(test_setup):
    strategy, spy_instr, aapl_instr = test_setup

    dates = pd.date_range("2020-01-01", periods=201, freq="D", tz="UTC")
    for d in dates[:200]:
        b = create_bar(spy_instr.id, str(d), 100, 105, 95, 100)
        strategy.spy_ema_200.handle_bar(b)
        strategy.on_bar(b)

    assert strategy.spy_ema_200.initialized

    b_down = create_bar(spy_instr.id, str(dates[200]), 90, 95, 85, 90)

    with patch.object(type(strategy), 'portfolio', new_callable=MagicMock) as mock_portfolio:
        mock_portfolio.positions.return_value = []
        strategy.spy_ema_200.handle_bar(b_down)
        strategy.on_bar(b_down)
        assert strategy.spy_close_under_ema == True

        strategy.active_signals[aapl_instr.id] = 5.0
        strategy.process_entries()
        assert len(strategy.active_signals) == 0

def test_trailing_stop_ratchet(test_setup):
    strategy, spy_instr, aapl_instr = test_setup
    aapl = aapl_instr.id

    dates = pd.date_range("2020-01-01", periods=15, freq="D", tz="UTC")
    for d in dates[:14]:
        b = create_bar(aapl, str(d), 100, 110, 90, 100)
        strategy.atr_14[aapl].handle_bar(b)
        strategy.ema_20[aapl].handle_bar(b)
        strategy.rsi_14[aapl].handle_bar(b)
        strategy.bb_20_2[aapl].handle_bar(b)
        strategy.roc_60[aapl].handle_bar(b)
        strategy.on_bar(b)

    atr_val = strategy.atr_14[aapl].value

    strategy.position_state = {}
    entry_price = 100.0
    initial_stop = entry_price - (2.0 * atr_val)

    # Create a bar to get its ts_init as entry_time
    entry_bar = create_bar(aapl, str(dates[13]), 100, 110, 90, 100)
    strategy.position_state[aapl] = {
        'stop_loss': initial_stop,
        'take_profit': entry_price + (3.0 * atr_val),
        'entry_time': entry_bar.ts_init,
        'entry_price': entry_price
    }

    b_up = create_bar(aapl, str(dates[14]), 120, 125, 115, 120)
    with patch.object(type(strategy), 'portfolio', new_callable=MagicMock) as mock_portfolio,          patch.object(type(strategy), 'cache', new_callable=MagicMock) as mock_cache,          patch.object(type(strategy), 'order_factory', new_callable=MagicMock) as mock_order_factory,          patch.object(WSBConfluenceStrategy, 'submit_order') as mock_submit:
        mock_cache.instrument.return_value = aapl_instr
        mock_portfolio.position.return_value = MagicMock()
        strategy.manage_exits(aapl, b_up)

    new_stop = strategy.position_state[aapl]['stop_loss']
    assert new_stop > initial_stop

    b_down = create_bar(aapl, str(dates[14] + pd.Timedelta(days=1)), 110, 115, 105, 110)
    with patch.object(type(strategy), 'portfolio', new_callable=MagicMock) as mock_portfolio,          patch.object(type(strategy), 'cache', new_callable=MagicMock) as mock_cache,          patch.object(type(strategy), 'order_factory', new_callable=MagicMock) as mock_order_factory,          patch.object(WSBConfluenceStrategy, 'submit_order') as mock_submit:
        mock_cache.instrument.return_value = aapl_instr
        mock_portfolio.position.return_value = MagicMock()
        strategy.manage_exits(aapl, b_down)

    assert math.isclose(strategy.position_state[aapl]['stop_loss'], new_stop)

def test_risk_parity_sizing(test_setup):
    strategy, spy_instr, aapl_instr = test_setup
    aapl = aapl_instr.id

    dates = pd.date_range("2020-01-01", periods=15, freq="D", tz="UTC")
    for d in dates[:14]:
        b = create_bar(aapl, str(d), 100, 110, 90, 100)
        strategy.atr_14[aapl].handle_bar(b)
        strategy.ema_20[aapl].handle_bar(b)
        strategy.rsi_14[aapl].handle_bar(b)
        strategy.bb_20_2[aapl].handle_bar(b)
        strategy.roc_60[aapl].handle_bar(b)
        strategy.on_bar(b)

    atr_val = strategy.atr_14[aapl].value

    strategy.active_signals[aapl] = 10.0
    strategy.spy_close_under_ema = False

    last_b = create_bar(aapl, str(dates[14]), 100, 105, 95, 100)

    with patch.object(type(strategy), 'portfolio', new_callable=MagicMock) as mock_portfolio,          patch.object(type(strategy), 'cache', new_callable=MagicMock) as mock_cache,          patch.object(type(strategy), 'order_factory', new_callable=MagicMock) as mock_order_factory,          patch.object(WSBConfluenceStrategy, 'submit_order') as mock_submit:

        mock_portfolio.positions.return_value = []
        mock_portfolio.has_position.return_value = False
        mock_portfolio.margin_balance.return_value = 100000.0

        mock_cache.instrument.return_value = aapl_instr
        mock_cache.bar.return_value = last_b

        mock_order = MagicMock()
        mock_order_factory.market.return_value = mock_order

        strategy.process_entries()

        expected_shares = math.floor((100000 * 0.02) / (2.0 * atr_val))

        mock_order_factory.market.assert_called_once()
        kwargs = mock_order_factory.market.call_args[1]

        assert kwargs['instrument_id'] == aapl
        mock_submit.assert_called_once()
