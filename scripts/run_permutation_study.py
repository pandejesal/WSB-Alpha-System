import logging
import numpy as np
from src.backtest.validation import (
    load_base_data,
    run_in_sample_test,
    run_walk_forward_test,
    NUM_PERMUTATIONS,
    TEARSHEET_ENGINE,
)
from src.ops.audit import write_artifact

logger = logging.getLogger(__name__)

def run_study():
    """
    Runs the full 200-permutation protocol on the honest T+1 engine.
    Writes results to docs/data/permutation_study.json
    """
    logger.info("Starting permutation study (G4).")

    # E-1 guard check (just in case the module import didn't catch it)
    if getattr(TEARSHEET_ENGINE, "LEGACY_REFERENCE_ONLY", False):
        raise RuntimeError("E-1: tearsheet engine rebound to legacy engine.")

    # Load data
    try:
        posts_df, stock_dfs, spy_close = load_base_data()
    except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully on missing data
        logger.warning(f"Failed to load full backtest data: {e}. Writing safe fallback to permutation_study.json")
        # Write a failing G4 safely if data is missing during paper phase setup
        write_artifact("docs/data/permutation_study.json", {
            "p_value": 1.0,
            "status": "failed_data_load",
            "message": str(e)
        })
        return

    np.random.seed(42)

    try:
        real_ret, real_sharpe, permuted_rets, permuted_sharpes, in_sample_p_value, _, _ = run_in_sample_test(posts_df, stock_dfs, spy_close)
    except TypeError:
        # If run_in_sample_test fails
        logger.error("run_in_sample_test failed.")
        return

    try:
        real_pooled_ret, real_pooled_sharpe, pooled_permuted_rets, pooled_permuted_sharpes, walk_forward_p_value, walk_forward_win_rate, num_windows = run_walk_forward_test(posts_df, stock_dfs, spy_close)
    except TypeError:
        # If run_walk_forward_test fails
        logger.error("run_walk_forward_test failed.")
        return

    payload = {
        "in_sample_p_value": in_sample_p_value,
        "walk_forward_p_value": walk_forward_p_value,
        "walk_forward_win_rate": walk_forward_win_rate,
        "num_windows": num_windows,
        "permutations": NUM_PERMUTATIONS,
        "engine": "run_historic_backtest",
        "status": "success"
    }

    write_artifact("docs/data/permutation_study.json", payload)
    logger.info(f"Permutation study complete. in_sample_p_value={in_sample_p_value}, walk_forward_p_value={walk_forward_p_value}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_study()
