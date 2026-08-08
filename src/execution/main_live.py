import os
import sys
import logging
import json
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# Import components
from src.alpha.wsb_alpha_legacy import run_sentiment_pipeline, OUTPUT_CSV
from src.alpha.indicators import compute_indicators
from src.alpha.macro_regime import MacroRegimeFilter
from src.alpha.fade_strategy import FadeStrategy
from src.execution.execution_adapter import PaperbrokerClient, ExecutionAdapter
import yfinance as yf

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("live_trading.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables (API keys, Webhook URLs)
load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

def send_webhook_notification(signals: list):
    """Sends a summary of executed trades to Discord/Telegram."""
    if not DISCORD_WEBHOOK_URL:
        logger.warning("No webhook URL configured. Skipping notification.")
        return

    if not signals:
        message = "Daily Trading Run Complete. No trades executed today."
    else:
        message = f"**Daily Trading Run Complete. Executed {len(signals)} trades:**\n"
        for sig in signals:
            message += f"- {sig['strategy']}: {sig['side']} {sig['quantity']} ${sig['ticker']} (CVaR: {sig['target_cvar_allocation']:.4f})\n"

    payload = {"content": message}
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Webhook notification sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send webhook notification: {e}")

def get_latest_sentiment_data() -> pd.DataFrame:
    """Reads the latest sentiment data from the pipeline output."""
    if not os.path.exists(OUTPUT_CSV):
        logger.error(f"{OUTPUT_CSV} not found. Cannot proceed.")
        return pd.DataFrame()
    return pd.read_csv(OUTPUT_CSV)

def run_technical_and_risk_pipelines(df: pd.DataFrame, macro_filter: MacroRegimeFilter, fade_strategy: FadeStrategy) -> list:
    """
    Processes the sentiment dataframe to generate final trade signals,
    applying Technical Confluence, Macro Regime Filtering, and Risk Parity.
    """
    final_signals = []

    # Process only the most recent date's data
    if df.empty or 'date' not in df.columns:
        return final_signals

    latest_date = df['date'].max()
    latest_data = df[df['date'] == latest_date]
    logger.info(f"Processing {len(latest_data)} entries for {latest_date}")

    # Apply Macro Filter (fetch SPY regime)
    macro_filter.fetch_regime()

    # Iterate over tickers to evaluate technicals and risk
    for _, row in latest_data.iterrows():
        ticker = row['ticker']
        sentiment_score = row['sentiment_score']

        try:
            # Download recent data for technical indicators (need at least 20 days, fetch 60 for safety)
            stock_data = yf.download(ticker, period="60d", interval="1d", progress=False)
            if len(stock_data) < 20:
                logger.warning(f"Not enough price history for {ticker}. Skipping.")
                continue

            # Compute indicators
            stock_data = compute_indicators(stock_data)
            if stock_data is None:
                continue

            latest_tech = stock_data.iloc[-1]

            # 1. Evaluate Fade Strategy
            fade_signal = fade_strategy.generate_signal(
                ticker=ticker,
                current_score=sentiment_score,
                technical_data=latest_tech,
                base_qty=10, # Stub sizing
                cvar=latest_tech.get('CVaR_95', 0.05)
            )

            if fade_signal:
                # Apply Macro Filter and append
                filtered_signal = macro_filter.apply_filter(fade_signal)
                if filtered_signal.get('status') != 'REJECTED':
                    final_signals.append(filtered_signal)
                continue # If faded, skip alpha fusion

            # 2. Evaluate Alpha Fusion Confluence
            # (Heikin-Ashi, 20 EMA, 14 RSI, MACD using a 2-out-of-3 channel consensus)
            ha_bullish = latest_tech['HA_Close'] > latest_tech['HA_Open']
            ema_bullish = latest_tech['Close'] > latest_tech['EMA_20']
            macd_bullish = latest_tech['MACD'] > latest_tech['MACD_Signal']
            rsi_neutral = 30 < latest_tech['RSI_14'] < 70

            confluence_score = int(ha_bullish) + int(ema_bullish) + int(macd_bullish)

            if confluence_score >= 2 and sentiment_score > 0.5 and rsi_neutral:
                # Alpha Fusion BUY Signal
                alpha_signal = {
                    "ticker": ticker,
                    "side": "BUY",
                    "quantity": 10, # Stub sizing, ideally derived from src.risk parity
                    "order_type": "MARKET",
                    "target_cvar_allocation": latest_tech.get('CVaR_95', 0.05),
                    "confluence_score": confluence_score,
                    "strategy": "AlphaFusion"
                }

                # Apply Macro Filter (e.g. SPY BEAR regime slashes sizing)
                filtered_signal = macro_filter.apply_filter(alpha_signal)
                if filtered_signal.get('status') != 'REJECTED':
                    # Clean up internal tracking fields before sending to broker
                    filtered_signal.pop('status', None)
                    filtered_signal.pop('reject_reason', None)
                    filtered_signal.pop('confluence_score', None)
                    final_signals.append(filtered_signal)

        except Exception as e:
            logger.error(f"Failed to process {ticker}: {e}")

    return final_signals

def main():
    logger.info("=== STARTING LIVE TRADING ORCHESTRATOR ===")

    try:
        # Step 1: Run Sentiment Pipeline (Scraping + FinBERT)
        logger.info("Running sentiment pipeline...")
        success = run_sentiment_pipeline()
        if not success:
            logger.error("Sentiment pipeline failed. Aborting live trading run.")
            return

        df = get_latest_sentiment_data()

        # Step 2: Initialize Strategies & Filters
        macro_filter = MacroRegimeFilter()

        # Calculate historical 90th percentile sentiment over the trailing 30 days
        historical_90th = None
        if not df.empty and 'date' in df.columns:
            # Ensure date column is datetime
            df['date'] = pd.to_datetime(df['date'])
            latest_date = df['date'].max()
            thirty_days_ago = latest_date - pd.Timedelta(days=30)

            # Filter historical window (excluding today to form the baseline)
            historical_mask = (df['date'] >= thirty_days_ago) & (df['date'] < latest_date)
            historical_data = df[historical_mask]

            if len(historical_data) >= 10: # Minimum sample size for percentile
                import numpy as np
                historical_90th = np.percentile(historical_data['sentiment_score'].dropna(), 90)
                logger.info(f"Calculated trailing 30-day 90th percentile sentiment threshold: {historical_90th:.4f}")
            else:
                logger.info("Not enough historical data in the trailing 30 days to compute 90th percentile.")

        fade_strategy = FadeStrategy(historical_90th_percentile=historical_90th)

        # Step 3: Run Technical & Risk Management Pipelines
        logger.info("Evaluating technicals and risk parity...")
        final_signals = run_technical_and_risk_pipelines(df, macro_filter, fade_strategy)

        # Step 4: Execute via Paper Trading Bridge
        logger.info(f"Generated {len(final_signals)} final trade signals.")
        if final_signals:
            broker = PaperbrokerClient(
                base_url=os.getenv("PAPERBROKER_URL", "http://localhost:5000"),
                api_key=os.getenv("PAPERBROKER_API_KEY", "")
            )
            adapter = ExecutionAdapter(broker)
            execution_results = adapter.execute_signals(final_signals)
            logger.info(f"Execution Results: {json.dumps(execution_results, indent=2)}")

        # Step 5: Send Webhook Notifications
        send_webhook_notification(final_signals)

    except Exception as e:
        logger.exception(f"Critical error in live trading orchestrator: {e}")
    finally:
        logger.info("=== LIVE TRADING ORCHESTRATOR FINISHED ===")

if __name__ == "__main__":
    main()
