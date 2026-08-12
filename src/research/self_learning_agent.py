import json
import logging
import os
import sqlite3

import numpy as np
import pandas as pd
import yaml
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Pydantic Configuration Model with Guardrails ---
class StrategyConfig(BaseModel):
    cvar_threshold: float = Field(..., ge=0.05, le=0.20, description="CVaR Threshold")
    order_block_min_atr_mult: float = Field(..., ge=0.5, le=3.0, description="Order Block Minimum ATR Multiplier")
    sentiment_threshold: float = Field(..., ge=0.70, le=0.99, description="Sentiment Threshold")
    take_profit_atr_mult: float = Field(..., ge=1.0, le=5.0, description="Take Profit ATR Multiplier")
    stop_loss_atr_mult: float = Field(..., ge=0.5, le=2.5, description="Stop Loss ATR Multiplier")

class SelfOptimizer:
    def __init__(self, db_path: str = "trades.db", config_path: str = "strategy_config.yaml"):
        self.db_path = db_path
        self.config_path = config_path

        # Gemini Client - Key expected from environment variables
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not self.gemini_api_key:
            logger.warning("GEMINI_API_KEY environment variable is not set. LLM optimization will fail.")
        self.client = genai.Client(api_key=self.gemini_api_key)

        # Performance Goals
        self.TARGET_MAX_DD = -0.15 # 15% Max DD
        self.TARGET_SHARPE = 1.5

    def _init_db(self):
        """Initializes the SQLite schema if it does not exist."""
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

    def load_recent_trades(self, days: int = 30) -> pd.DataFrame:
        """Loads the last 30 days of trades into a pandas DataFrame."""
        self._init_db()
        query = f"SELECT * FROM trades WHERE exit_time >= date('now', '-{days} days')"
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, parse_dates=['entry_time', 'exit_time'])
        return df

    def calculate_metrics(self, df: pd.DataFrame) -> dict:
        """Calculates performance metrics for the trades."""
        if df.empty:
            return {"sharpe": 0.0, "win_rate": 0.0, "max_drawdown": 0.0}

        # Win Rate
        win_rate = len(df[df['pnl_pct'] > 0]) / len(df)

        # Sharpe Ratio (Assuming pnl_pct represents trade return and using 0% risk-free rate for simplicity)
        # Using typical 252 trading days approximation, but scaled for trades.
        # Standard calculation: Mean / StdDev * sqrt(N)
        returns = df['pnl_pct']
        mean_return = returns.mean()
        std_return = returns.std()

        # To get an annualized sharpe from trades, we need to know the frequency.
        # Given it's a generic evaluation, let's just use the classic per-trade sharpe
        # or an annualized version assuming 252 days and scaling by trades/day.
        # We will use per-trade Sharpe * sqrt(trades per year) approximation.
        trades_per_day = len(df) / 30.0 if len(df) > 0 else 0
        trades_per_year = trades_per_day * 252

        sharpe = (mean_return / std_return) * np.sqrt(trades_per_year) if std_return > 0 else 0.0

        # Maximum Drawdown
        # Create a cumulative equity curve starting at 1.0
        equity_curve = (1 + returns).cumprod()
        running_max = equity_curve.cummax()
        drawdown = (equity_curve - running_max) / running_max
        max_drawdown = drawdown.min()

        return {
            "sharpe": sharpe,
            "win_rate": win_rate,
            "max_drawdown": max_drawdown
        }

    def _needs_optimization(self, metrics: dict) -> bool:
        """Checks if the system is underperforming."""
        return bool(metrics['sharpe'] < self.TARGET_SHARPE or metrics['max_drawdown'] < self.TARGET_MAX_DD)

    def load_current_config(self) -> dict:
        """Loads the current configuration from YAML."""
        if not os.path.exists(self.config_path):
            # Safe defaults
            return {
                "cvar_threshold": 0.10,
                "order_block_min_atr_mult": 1.5,
                "sentiment_threshold": 0.85,
                "take_profit_atr_mult": 2.0,
                "stop_loss_atr_mult": 1.0
            }
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def save_config(self, config_data: dict):
        """Safely saves the configuration to YAML."""
        with open(self.config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False)

    def ask_llm_for_parameters(self, metrics: dict, df: pd.DataFrame, current_config: dict) -> dict | None:
        """Queries Gemini to propose new parameters using tool calling."""

        # Summarize trades for context to avoid huge payloads
        trade_summary = df.describe().to_dict()

        prompt = f"""
        Analyze this recent trade history and performance metrics.
        Current Metrics: {json.dumps(metrics, indent=2)}
        Target Metrics: Sharpe > {self.TARGET_SHARPE}, Max Drawdown < {self.TARGET_MAX_DD * 100}%
        Current Config: {json.dumps(current_config, indent=2)}
        Trade Summary (MFE/MAE/PnL stats): {json.dumps(trade_summary, indent=2)}

        Provide a JSON output with adjusted strategy parameters to reduce drawdown and increase profit factor.
        """

        tool = types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="update_strategy_parameters",
                    description="Updates strategy parameters based on performance analysis.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "cvar_threshold": types.Schema(type=types.Type.NUMBER, description="CVaR Threshold (0.05 - 0.20)"),
                            "order_block_min_atr_mult": types.Schema(type=types.Type.NUMBER, description="Order Block Min ATR Mult (0.5 - 3.0)"),
                            "sentiment_threshold": types.Schema(type=types.Type.NUMBER, description="Sentiment Threshold (0.70 - 0.99)"),
                            "take_profit_atr_mult": types.Schema(type=types.Type.NUMBER, description="Take Profit ATR Mult (1.0 - 5.0)"),
                            "stop_loss_atr_mult": types.Schema(type=types.Type.NUMBER, description="Stop Loss ATR Mult (0.5 - 2.5)")
                        },
                        required=["cvar_threshold", "order_block_min_atr_mult", "sentiment_threshold", "take_profit_atr_mult", "stop_loss_atr_mult"]
                    )
                )
            ]
        )

        try:
            response = self.client.models.generate_content(
                model="gemini-3.1-pro-preview-customtools",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[tool]
                )
            )

            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.function_call and part.function_call.name == "update_strategy_parameters":
                        # Convert dict-like structure to dict if needed
                        return dict(part.function_call.args)

            logger.error("LLM did not return the expected tool call.")
            return None

        except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
            logger.error(f"Error querying LLM: {e}")
            return None

    def run_optimization_cycle(self):
        """Runs the full evaluation and optimization loop."""
        logger.info("Starting Self-Reflection & Auto-Optimization Engine...")

        df = self.load_recent_trades(days=30)
        metrics = self.calculate_metrics(df)
        logger.info(f"Recent Metrics: {metrics}")

        current_config = self.load_current_config()

        if self._needs_optimization(metrics):
            logger.info("System underperforming. Initiating LLM optimization...")
            new_params = self.ask_llm_for_parameters(metrics, df, current_config)

            if new_params:
                try:
                    # Validate strictly with Pydantic
                    validated_config = StrategyConfig(**new_params)

                    # If valid, save it
                    self.save_config(validated_config.model_dump())
                    logger.info("Successfully optimized and updated strategy_config.yaml.")
                except ValidationError as e:
                    logger.error(f"LLM hallucinated invalid parameters. Rejecting update.\nValidation Error: {e}")
                    logger.info("Reverting to previous safe configuration.")
            else:
                logger.warning("Failed to obtain new parameters from LLM.")
        else:
            logger.info("System is meeting performance targets. No optimization required.")

if __name__ == "__main__":
    optimizer = SelfOptimizer()
    optimizer.run_optimization_cycle()
