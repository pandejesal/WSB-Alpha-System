import asyncio
import logging
import os
from abc import ABC, abstractmethod

import aiohttp

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Telegram Alerting ---
async def send_telegram_alert(message: str):
    """Sends an asynchronous message to the configured Telegram bot."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        logger.warning("Telegram credentials not found. Skipping webhook alert.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        async with aiohttp.ClientSession() as session:  # noqa: SIM117 - Nested with is more readable here
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    logger.error(f"Failed to send Telegram alert: {await response.text()}")
                else:
                    logger.info("Telegram alert sent successfully.")
    except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
        logger.error(f"Exception during Telegram alert: {e}")

# --- Abstract Base Interface ---
class BaseExecutor(ABC):
    @abstractmethod
    def get_account_equity(self) -> float:
        pass

    @abstractmethod
    def execute_order(self, ticker: str, direction: str, quantity: float, price: float | None = None) -> bool:
        pass

    @abstractmethod
    def liquidate_strategy_positions(self, strategy_id: str):
        pass


# --- Implementations (routing to real brokers) ---
class AlpacaExecutor(BaseExecutor):
    def __init__(self):
        from src.execution.alpaca_broker import AlpacaBroker
        self.broker = AlpacaBroker()

    def get_account_equity(self) -> float:
        try:
            return float(self.broker.get_account_balance().get('equity', 0.0))
        except Exception as e:  # noqa: BLE001
            logger.error(f"[Alpaca] Failed to get equity: {e}")
            return 0.0

    def execute_order(self, ticker: str, direction: str, quantity: float, price: float | None = None) -> bool:
        logger.info(f"[Alpaca] Executing {direction} order for {quantity} of {ticker}")
        try:
            res = self.broker.place_order(ticker, quantity, direction)
            return res.get('status') == 'success'
        except Exception as e:  # noqa: BLE001
            logger.error(f"[Alpaca] Order failed: {e}")
            return False

    def liquidate_strategy_positions(self, strategy_id: str):
        # Alpaca doesn't natively support strategy tags in this wrapper yet,
        # so we log it. A full implementation would map strategy_id to positions.
        logger.info(f"[Alpaca] Liquidating positions for strategy {strategy_id}")


class CryptoExecutor(BaseExecutor):
    def __init__(self):
        from src.execution.ccxt_broker import CCXTBroker
        self.broker = CCXTBroker()

    def get_account_equity(self) -> float:
        try:
            return float(self.broker.get_account_balance().get('equity', 0.0))
        except Exception as e:  # noqa: BLE001
            logger.error(f"[Crypto] Failed to get equity: {e}")
            return 0.0

    def execute_order(self, ticker: str, direction: str, quantity: float, price: float | None = None) -> bool:
        logger.info(f"[Crypto] Executing {direction} order for {quantity} of {ticker}")
        try:
            res = self.broker.place_order(ticker, quantity, direction)
            return res.get('status') == 'success'
        except Exception as e:  # noqa: BLE001
            logger.error(f"[Crypto] Order failed: {e}")
            return False

    def liquidate_strategy_positions(self, strategy_id: str):
        logger.info(f"[Crypto] Liquidating positions for strategy {strategy_id}")


# --- Universal Broker ---
class UniversalBroker:
    def __init__(self):
        self.alpaca_executor = AlpacaExecutor()
        self.crypto_executor = CryptoExecutor()
        self.MAX_RISK_PER_TRADE_PCT = 0.01  # 1% max account equity risk

    def get_executor(self, asset_class: str) -> BaseExecutor:
        if asset_class.lower() == 'crypto':
            return self.crypto_executor
        else:
            return self.alpaca_executor

    async def place_order(self, asset_class: str, strategy_id: str, ticker: str, direction: str, quantity: float, risk_amount: float):
        """Intercepts, validates risk, and executes an order."""

        executor = self.get_executor(asset_class)
        equity = executor.get_account_equity()

        # Position Sizing Interceptor (Risk Check)
        max_allowed_risk = equity * self.MAX_RISK_PER_TRADE_PCT
        if risk_amount > max_allowed_risk:
            logger.warning(f"Risk Intercept! Trade risk ({risk_amount}) exceeds 1% of equity ({max_allowed_risk}). Halting order.")
            # Alternatively, we could downsize the quantity here.
            return False

        logger.info(f"Risk check passed. Routing {ticker} {direction} order to {asset_class} executor.")

        success = executor.execute_order(ticker, direction, quantity)

        if success:
            msg = f"⚡ <b>EXECUTION:</b> {direction} {quantity} {ticker} (Strategy: {strategy_id})"
            await send_telegram_alert(msg)

        return success

    async def handle_promotion(self, strategy_id: str, metrics: dict):
        """Callback for Incubation Manager."""
        msg = f"🟢 <b>PROMOTION:</b> Strategy <code>{strategy_id}</code> upgraded to LIVE.\nMetrics: {metrics}"
        await send_telegram_alert(msg)

    async def handle_demotion(self, strategy_id: str, metrics: dict):
        """Callback for Incubation Manager."""
        msg = f"🔴 <b>DEMOTION:</b> Strategy <code>{strategy_id}</code> demoted to DEPRECATED.\nMetrics: {metrics}\nLiquidating positions..."
        await send_telegram_alert(msg)

        # Liquidate across all potential executors
        self.alpaca_executor.liquidate_strategy_positions(strategy_id)
        self.crypto_executor.liquidate_strategy_positions(strategy_id)

if __name__ == "__main__":
    # Quick test
    async def test():
        broker = UniversalBroker()
        await broker.place_order("crypto", "alpha_v1", "BTC-USD", "BUY", 0.05, 40.0) # Assume 40 risk is < 1% of 5000 (50)

    asyncio.run(test())
