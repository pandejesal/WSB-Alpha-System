import json
import logging
import os
from datetime import datetime, timezone

from src.research.browser_scraper import fetch_headlines, score_text
from src.research.debate_engine import DebateEngine
from src.risk.fred_macro_provider import FredMacroProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting research pipeline...")

    # Load universe
    universe_path = "config/universe.json"
    tickers = []
    if os.path.exists(universe_path):
        with open(universe_path, "r") as f:
            data = json.load(f)
            tickers = data.get("tickers", [])
    else:
        logger.warning(f"Universe file {universe_path} not found. Using default list.")
        tickers = ["SPY", "AAPL", "MSFT"]

    # Initialize FRED provider for macro context
    macro_provider = FredMacroProvider()
    try:
        regime_mult = macro_provider.regime_multiplier()
        logger.info(f"Macro regime multiplier: {regime_mult}")
    except Exception as e:
        logger.warning(f"Failed to get macro regime multiplier: {e}. Defaulting to 1.0.")
        regime_mult = 1.0

    results = []
    current_date = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    debate_engine = DebateEngine()

    for ticker in tickers:
        try:
            # 1. Fetch headlines (gracefully degrades to mock if no real scraper implemented)
            headlines = fetch_headlines(ticker)

            # 2. Score headlines
            base_score = score_text(headlines)

            # 3. Debate engine to get consensus
            debate_result = debate_engine.run_debate(ticker, headlines, base_score)

            base_q_score = debate_result.get("score", 0.0)
            stance = debate_result.get("stance", "neutral")
            reasoning = " | ".join(debate_result.get("reasoning", []))

            # 4. Apply macro regime multiplier
            adjusted_score = base_q_score * regime_mult

            results.append({
                "ticker": ticker,
                "date": current_date,
                "score": round(adjusted_score, 4),
                "stance": stance.upper(),
                "reasoning": reasoning,
                "source": "ResearchPipeline"
            })
            logger.info(f"Processed {ticker}: Stance={stance.upper()}, Score={adjusted_score:.4f}")
        except Exception as e:
            logger.error(f"Failed to process research for {ticker}: {e}")

    # Persist results
    out_dir = "docs/data"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "research_sentiment.json")

    try:
        with open(out_file, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"Successfully saved research results to {out_file}")
    except Exception as e:
        logger.error(f"Failed to save research results to {out_file}: {e}")

if __name__ == "__main__":
    main()
