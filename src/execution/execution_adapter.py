import abc
import json
import logging
import requests

logger = logging.getLogger(__name__)

class PaperTradeBroker(abc.ABC):
    """Abstract Base Class for Paper Trading Brokers."""

    @abc.abstractmethod
    def place_order(self, ticker: str, qty: int, side: str, order_type: str = "MARKET", target_cvar_allocation: float = 0.0) -> dict:
        pass

    @abc.abstractmethod
    def get_portfolio(self) -> dict:
        pass

    @abc.abstractmethod
    def get_open_positions(self) -> dict:
        pass

class PaperbrokerClient(PaperTradeBroker):
    """Concrete implementation for the 'paperbroker' API."""

    def __init__(self, base_url: str = "http://localhost:5000", api_key: str = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    def place_order(self, ticker: str, qty: int, side: str, order_type: str = "MARKET", target_cvar_allocation: float = 0.0) -> dict:
        endpoint = f"{self.base_url}/order"
        payload = {
            "ticker": ticker.upper(),
            "side": side.upper(),
            "quantity": int(qty),
            "order_type": order_type.upper(),
            "target_cvar_allocation": float(target_cvar_allocation)
        }

        try:
            response = requests.post(endpoint, json=payload, headers=self.headers, timeout=10)
            response.raise_for_status()
            logger.info(f"Successfully placed order for {qty} {ticker} {side}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to place order for {ticker}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return {"status": "error", "message": str(e)}

    def get_portfolio(self) -> dict:
        endpoint = f"{self.base_url}/portfolio"
        try:
            response = requests.get(endpoint, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get portfolio: {e}")
            return {"status": "error", "message": str(e)}

    def get_open_positions(self) -> dict:
        endpoint = f"{self.base_url}/positions"
        try:
            response = requests.get(endpoint, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get open positions: {e}")
            return {"status": "error", "message": str(e)}

class ExecutionAdapter:
    """Formats raw trade signals and routes them to the broker."""

    def __init__(self, broker: PaperTradeBroker):
        self.broker = broker

    def execute_signals(self, signals: list) -> list:
        """
        Takes a list of dictionaries containing trade signals and executes them.
        Expected keys in each signal dict: 'ticker', 'side', 'quantity', 'target_cvar_allocation'
        """
        results = []
        for signal in signals:
            if not all(k in signal for k in ('ticker', 'side', 'quantity')):
                logger.warning(f"Invalid signal format: {signal}")
                continue

            ticker = signal['ticker']
            side = signal['side']
            qty = signal['quantity']
            cvar = signal.get('target_cvar_allocation', 0.0)
            order_type = signal.get('order_type', 'MARKET')

            logger.info(f"Executing signal: {side} {qty} {ticker} (CVaR: {cvar})")
            result = self.broker.place_order(ticker, qty, side, order_type, cvar)
            results.append({
                "signal": signal,
                "result": result
            })

        return results
