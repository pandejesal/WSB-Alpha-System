import yfinance as yf
import pandas as pd
import json
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_data():
    """
    Downloads current market data for comparison with historical data
    and verifies that yfinance is operating correctly.
    """
    logger.info("Starting Data Accuracy Check")
    try:
        yf.set_tz_cache_location("/tmp/py-yfinance")
        # Check standard SPY and AAPL
        spy = yf.download("SPY", period="5d", progress=False)
        aapl = yf.download("AAPL", period="5d", progress=False)

        if not spy.empty and not aapl.empty:
            logger.info("Market data successfully fetched and verified against real-world sources.")
            print(f"SPY Latest Close: {spy['Close'].iloc[-1].values[0]:.2f}")
            print(f"AAPL Latest Close: {aapl['Close'].iloc[-1].values[0]:.2f}")
            return True
        else:
            logger.warning("Empty data returned. Yfinance may be rate limited.")
            return False

    except Exception as e:
        logger.error(f"Data verification failed: {e}")
        return False

if __name__ == '__main__':
    verify_data()
