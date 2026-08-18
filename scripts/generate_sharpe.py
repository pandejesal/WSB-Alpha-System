import json
import logging
import os
import numpy as np

from src.ops.audit import write_artifact

logger = logging.getLogger(__name__)

def calculate_sharpe(returns: list[float], risk_free_rate: float = 0.0) -> dict:
    """Calculates Sharpe Ratio with a simple Confidence Interval."""
    if not returns:
        return {"sharpe": 0.0, "ci_lower": 0.0, "ci_upper": 0.0}

    returns_arr = np.array(returns)
    mean = np.mean(returns_arr) - risk_free_rate
    std = np.std(returns_arr)

    if std == 0:
        return {"sharpe": 0.0, "ci_lower": 0.0, "ci_upper": 0.0}

    sharpe = (mean / std) * np.sqrt(252) # Annualized

    # Approx Standard Error for Sharpe = sqrt((1 + 0.5 * sharpe^2) / n)
    n = len(returns)
    se = np.sqrt((1 + 0.5 * sharpe**2) / n)

    ci_lower = sharpe - 1.96 * se
    ci_upper = sharpe + 1.96 * se

    return {
        "sharpe": sharpe,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper
    }

def main():
    logging.basicConfig(level=logging.INFO)
    logger.info("Generating Sharpe Ratio Report...")

    portfolio_file = "docs/data/portfolio_state.json"
    returns = []
    if os.path.exists(portfolio_file):
        try:
            with open(portfolio_file, "r") as f:
                p_data = json.load(f)
                history = p_data.get("history", [])

                for i in range(1, len(history)):
                    prev_eq = history[i-1].get("equity", 100.0)
                    curr_eq = history[i].get("equity", 100.0)
                    if prev_eq > 0:
                        ret = (curr_eq - prev_eq) / prev_eq
                        returns.append(ret)
        except Exception as e:
            logger.error(f"Failed to parse portfolio state: {e}")

    if not returns:
        logger.warning("No returns history found, using default 0.0")
        returns = [0.0]

    result = calculate_sharpe(returns)
    result["n_trades"] = len(returns) # Using days as a proxy for trades in this aggregate view

    os.makedirs("docs/data/paper", exist_ok=True)
    write_artifact("docs/data/paper/sharpe.json", result)
    logger.info(f"Sharpe Report written: {result}")

if __name__ == "__main__":
    main()
