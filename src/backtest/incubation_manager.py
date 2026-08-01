import json
import logging
import os
import sqlite3
from enum import Enum

import pandas as pd
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StrategyState(str, Enum):
    INCUBATION = "INCUBATION"
    LIVE = "LIVE"
    DEPRECATED = "DEPRECATED"

class StrategyProfile(BaseModel):
    strategy_id: str
    state: StrategyState
    # Other metadata could be added here, e.g., config snapshot

class StrategyStateManager:
    def __init__(self, db_path: str = "trades.db", state_file: str = "strategy_states.json"):
        self.db_path = db_path
        self.state_file = state_file

        # Performance Thresholds
        self.GRADUATION_MIN_TRADES = 100
        self.GRADUATION_PROFIT_FACTOR = 1.4
        self.GRADUATION_MAX_DD = -0.05 # 5% Drawdown

        self.DEMOTION_MAX_DD = -0.10 # 10% Drawdown

        # Webhook callback for UniversalBroker (if needed) or simple async hooks
        self.on_promotion_callback = None
        self.on_demotion_callback = None

    def _init_db(self):
        """Ensure trades table exists so we don't crash if reading first."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    trade_id TEXT PRIMARY KEY,
                    ticker TEXT,
                    direction TEXT,
                    entry_time DATETIME,
                    exit_time DATETIME,
                    entry_price REAL,
                    exit_price REAL,
                    pnl_pct REAL,
                    mfe REAL,
                    mae REAL,
                    strategy_id TEXT
                )
            ''')
            conn.commit()

    def load_states(self) -> dict[str, StrategyProfile]:
        """Loads strategy states from JSON."""
        if not os.path.exists(self.state_file):
            return {}
        with open(self.state_file, 'r') as f:
            data = json.load(f)
            return {k: StrategyProfile(**v) for k, v in data.items()}

    def save_states(self, states: dict[str, StrategyProfile]):
        """Saves strategy states to JSON."""
        with open(self.state_file, 'w') as f:
            # Pydantic v2 dump
            data = {k: v.model_dump() for k, v in states.items()}
            json.dump(data, f, indent=4)

    def load_strategy_trades(self, strategy_id: str, days: int = 30) -> pd.DataFrame:
        """Loads recent trades for a specific strategy."""
        self._init_db()
        query = f"SELECT * FROM trades WHERE strategy_id = ? AND exit_time >= date('now', '-{days} days')"
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=(strategy_id,), parse_dates=['entry_time', 'exit_time'])
        return df

    def load_all_strategy_trades(self) -> pd.DataFrame:
        """Loads all recent trades."""
        self._init_db()
        query = "SELECT * FROM trades"
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, parse_dates=['entry_time', 'exit_time'])
        return df

    def calculate_metrics(self, df: pd.DataFrame) -> dict:
        """Calculates Profit Factor and Max Drawdown."""
        if df.empty:
            return {"profit_factor": 0.0, "max_drawdown": 0.0, "trade_count": 0}

        returns = df['pnl_pct']

        # Profit Factor: Gross Profit / Gross Loss
        gross_profit = returns[returns > 0].sum()
        gross_loss = abs(returns[returns < 0].sum())
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')

        # Maximum Drawdown
        equity_curve = (1 + returns).cumprod()
        running_max = equity_curve.cummax()
        drawdown = (equity_curve - running_max) / running_max
        max_drawdown = drawdown.min()

        return {
            "profit_factor": profit_factor,
            "max_drawdown": max_drawdown,
            "trade_count": len(df)
        }

    def evaluate_incubation_strategies(self):
        """Evaluates INCUBATION strategies for graduation."""
        logger.info("Evaluating INCUBATION strategies for graduation...")
        states = self.load_states()

        for strategy_id, profile in states.items():
            if profile.state == StrategyState.INCUBATION:
                # Assuming 30 days is our lookback for incubation validation, or all trades
                df = self.load_strategy_trades(strategy_id, days=30)
                metrics = self.calculate_metrics(df)

                logger.info(f"Strategy {strategy_id} (INCUBATION): {metrics}")

                if (metrics['trade_count'] >= self.GRADUATION_MIN_TRADES and
                    metrics['profit_factor'] > self.GRADUATION_PROFIT_FACTOR and
                    metrics['max_drawdown'] >= self.GRADUATION_MAX_DD): # Note: DD is negative

                    logger.info(f"Strategy {strategy_id} meets graduation criteria. Upgrading to LIVE.")
                    states[strategy_id].state = StrategyState.LIVE

                    if self.on_promotion_callback:
                        self.on_promotion_callback(strategy_id, metrics)

        self.save_states(states)

    def evaluate_live_strategies_realtime(self, latest_trade_df: pd.DataFrame = None):
        """Evaluates LIVE strategies for demotion. Should be called frequently."""
        logger.info("Evaluating LIVE strategies for demotion risk...")
        states = self.load_states()

        # We need all history to calculate peak-to-trough correctly
        all_trades = self.load_all_strategy_trades()

        for strategy_id, profile in states.items():
            if profile.state == StrategyState.LIVE:
                strategy_trades = all_trades[all_trades['strategy_id'] == strategy_id]
                metrics = self.calculate_metrics(strategy_trades)

                if metrics['max_drawdown'] <= self.DEMOTION_MAX_DD: # E.g., -0.12 <= -0.10
                    logger.warning(f"Strategy {strategy_id} violated risk threshold! Demoting to DEPRECATED.")
                    states[strategy_id].state = StrategyState.DEPRECATED

                    # Liquidate positions logic would be triggered via webhook/callback
                    if self.on_demotion_callback:
                        self.on_demotion_callback(strategy_id, metrics)

        self.save_states(states)

    def register_strategy(self, strategy_id: str):
        """Registers a new strategy in INCUBATION state."""
        states = self.load_states()
        if strategy_id not in states:
            states[strategy_id] = StrategyProfile(strategy_id=strategy_id, state=StrategyState.INCUBATION)
            self.save_states(states)
            logger.info(f"Registered new strategy: {strategy_id} in INCUBATION state.")

if __name__ == "__main__":
    manager = StrategyStateManager()
    # manager.register_strategy("alpha_v1")
    manager.evaluate_incubation_strategies()
    manager.evaluate_live_strategies_realtime()
