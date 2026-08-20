import json
import logging
import os
import numpy as np

from src.backtest.metrics import safe_sharpe
from src.ops.audit import write_artifact

logger = logging.getLogger(__name__)

def generate_sharpe():
    """
    Computes Sharpe ratio with CI of paper P&L and writes to docs/data/paper/sharpe.json
    """
    paper_dir = "docs/data/paper"
    # Check if we have paper_pnl.json containing the returns series.
    pnl_path = os.path.join(paper_dir, "pnl_series.json")
    if not os.path.exists(pnl_path):
        raise FileNotFoundError(f"Missing PnL series data for Sharpe calculation: {pnl_path}")

    try:
        with open(pnl_path, "r") as f:
            data = json.load(f)
            returns = data.get("returns", [])
    except Exception as e:
        raise ValueError(f"Failed to read {pnl_path}: {e}")

    if not returns:
        raise ValueError(f"No returns found in {pnl_path}")

    # Compute metrics
    import pandas as pd

    # Using a simple block bootstrap or normal approx for CI
    # CI ≈ Sharpe ± 1.96 * sqrt((1 + 0.5 * Sharpe^2) / N)
    ret_series = pd.Series(returns)
    sharpe = safe_sharpe(ret_series)
    n = len(ret_series)
    if n > 3:
        se = np.sqrt((1 + 0.5 * sharpe**2) / n)
        ci_lower = sharpe - 1.645 * se # 90% CI lower bound (1.645 for 90% two-sided is wrong, use 1.645 for one-sided? Paper gate asks for 90% CI, usually means 1.645)
        ci_upper = sharpe + 1.645 * se
    else:
        ci_lower = 0.0
        ci_upper = 0.0

    payload = {
        "sharpe": sharpe,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "n_samples": len(returns)
    }

    write_artifact(os.path.join(paper_dir, "sharpe.json"), payload)
    logger.info(f"Sharpe metrics written: {payload}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generate_sharpe()
