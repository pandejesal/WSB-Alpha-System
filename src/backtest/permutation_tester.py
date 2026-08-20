from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd


class PermutationValidator:
    """
    Monte Carlo Permutation Testing Engine.
    Validates trading strategies by generating synthetic price paths
    using logarithmic returns to preserve statistical moments while destroying serial correlation.
    """
    def __init__(self, num_permutations: int = 1000, p_value_threshold: float = 0.01, seed: int = 42, null_mode: str = "circular"):
        self.num_permutations = num_permutations
        self.p_value_threshold = p_value_threshold
        self.seed = seed
        self.null_mode = null_mode

    def _generate_synthetic_paths(self, df: pd.DataFrame, n_paths: int) -> np.ndarray:
        """
        Decomposes OHLC into log returns, shuffles inter-bar gaps and intra-bar returns,
        and reconstructs multiple synthetic paths instantaneously via vectorization.
        Returns array of shape (n_paths, len(df), 4) corresponding to (O, H, L, C)
        """
        # Convert prices to log space
        log_open = np.log(df['Open'].values)
        log_high = np.log(df['High'].values)
        log_low = np.log(df['Low'].values)
        log_close = np.log(df['Close'].values)

        n_bars = len(df)

        # 1. Calculate intra-bar dynamics (Log space)
        # We need these relative to Open to preserve the candle's shape exactly
        intra_high = log_high - log_open
        intra_low = log_low - log_open
        intra_close = log_close - log_open

        # Group these into a single geometry vector so a candle's H/L/C shape stays intact
        intra_geometry = np.column_stack((intra_high, intra_low, intra_close))

        # 2. Calculate inter-bar gaps (Log space)
        # Gap = Open(t) - Close(t-1)
        inter_gaps = np.zeros(n_bars)
        inter_gaps[1:] = log_open[1:] - log_close[:-1]

        # Prepare starting price for all paths
        base_price = log_open[0]

        # Allocate output array: paths x time x 4 (OHLC)
        synthetic_ohlc = np.zeros((n_paths, n_bars, 4), dtype=np.float64)
        rng = np.random.default_rng(self.seed)

        # Generate all paths
        for p in range(n_paths):
            if self.null_mode == "circular":
                lag = rng.integers(0, n_bars)
                shuf_geom = np.roll(intra_geometry, lag, axis=0)
                shuf_gaps = np.roll(inter_gaps, lag)
            else:
                # Shuffle indices
                # We shuffle the geometric shapes and gaps independently to destroy all serial correlation
                shuffled_geom_idx = rng.permutation(n_bars)
                shuffled_gap_idx = rng.permutation(n_bars)

                shuf_geom = intra_geometry[shuffled_geom_idx]
                shuf_gaps = inter_gaps[shuffled_gap_idx]

            # Reconstruct the log prices
            # The change from Open(t) to Open(t+1) = intra_close(t) + gap(t+1)
            # So Open(t) = base_price + cumsum(intra_close(t-1) + gap(t))

            step_returns = np.zeros(n_bars)
            step_returns[1:] = shuf_geom[:-1, 2] + shuf_gaps[1:]

            syn_log_open = base_price + np.cumsum(step_returns)
            syn_log_high = syn_log_open + shuf_geom[:, 0]
            syn_log_low = syn_log_open + shuf_geom[:, 1]
            syn_log_close = syn_log_open + shuf_geom[:, 2]

            synthetic_ohlc[p, :, 0] = syn_log_open
            synthetic_ohlc[p, :, 1] = syn_log_high
            synthetic_ohlc[p, :, 2] = syn_log_low
            synthetic_ohlc[p, :, 3] = syn_log_close

        # Convert back to arithmetic prices
        return np.exp(synthetic_ohlc)

    def validate(self, strategy_func: Callable[[pd.DataFrame], float], df: pd.DataFrame) -> dict[str, Any]:
        """
        Executes the in-sample permutation test.
        """
        # Run on Real Data
        real_profit_factor = strategy_func(df)

        if np.isnan(real_profit_factor) or real_profit_factor <= 1.0:
            return {
                "status": "FAILED",
                "p_value": 1.0,
                "real_profit_factor": real_profit_factor,
                "reason": "Strategy failed to produce a valid edge on original data."
            }

        # Generate Synthetic Paths
        print(f"Generating {self.num_permutations} synthetic paths...")
        synthetic_paths = self._generate_synthetic_paths(df, self.num_permutations)

        # Run on Permutations
        print("Evaluating strategy on synthetic noise data...")
        permuted_profit_factors = np.zeros(self.num_permutations)

        index_col = df.index
        for i in range(self.num_permutations):
            syn_df = pd.DataFrame({
                "Open": synthetic_paths[i, :, 0],
                "High": synthetic_paths[i, :, 1],
                "Low": synthetic_paths[i, :, 2],
                "Close": synthetic_paths[i, :, 3]
            }, index=index_col)

            pf = strategy_func(syn_df)
            permuted_profit_factors[i] = pf if not np.isnan(pf) else 0.0

        # Calculate P-Value
        count_exceed = np.sum(permuted_profit_factors >= real_profit_factor)
        p_value = count_exceed / self.num_permutations

        status = "PASSED" if p_value < self.p_value_threshold else "FAILED"

        return {
            "status": status,
            "p_value": p_value,
            "real_profit_factor": real_profit_factor,
            "mean_permuted_pf": np.mean(permuted_profit_factors)
        }


