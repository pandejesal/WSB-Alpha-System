import numpy as np
from arch.bootstrap import StationaryBootstrap
from scipy import stats


class StatisticalValidator:
    """
    Suite for evaluating the statistical robustness of trading strategies.
    """

    @staticmethod
    def whites_reality_check(strategy_returns: np.ndarray, benchmark_returns: np.ndarray, block_size: int = 10, replications: int = 1000) -> float:
        """
        White's Reality Check (Bootstrap Reality Check).
        Adjusts p-values for data-snooping bias across multiple parameter searches.
        Returns the adjusted p-value. Reject strategy if p >= 0.05.

        Args:
            strategy_returns: Array of strategy returns (or matrix for multiple strategies).
            benchmark_returns: Array of benchmark returns.
            block_size: Average block size for Stationary Bootstrap.
            replications: Number of bootstrap replications.
        """
        if len(strategy_returns) != len(benchmark_returns):
            raise ValueError("Strategy and benchmark returns must have the same length.")

        # If single strategy, reshape to 2D
        if strategy_returns.ndim == 1:
            strategy_returns = strategy_returns.reshape(-1, 1)

        # Calculate excess returns over benchmark
        excess_returns = strategy_returns - benchmark_returns.reshape(-1, 1)

        # Original test statistic (max mean excess return across all strategies)
        mean_excess_returns = np.mean(excess_returns, axis=0)
        t_stat = np.max(mean_excess_returns)

        # Center the excess returns to satisfy the null hypothesis (mean <= 0)
        centered_excess_returns = excess_returns - mean_excess_returns

        # Bootstrap
        bs = StationaryBootstrap(block_size, centered_excess_returns)


        bootstrap_t_stats = []
        for pos_data, _ in bs.bootstrap(replications):
            # pos_data is the resampled array/tuple, in this case we passed a single array so it's a tuple of len 1
            bs_data = pos_data[0]
            bs_mean = np.mean(bs_data, axis=0)
            bootstrap_t_stats.append(np.max(bs_mean))


        bootstrap_t_stats = np.array(bootstrap_t_stats)

        # Calculate p-value: proportion of bootstrapped t-stats greater than the original t-stat
        p_value = np.mean(bootstrap_t_stats >= t_stat)

        return p_value

    @staticmethod
    def spa_test(strategy_returns: np.ndarray, benchmark_returns: np.ndarray) -> dict:
        """
        Superior Predictive Ability (SPA) Test (Hansen's SPA).
        A simpler proxy implemented using scipy for basic comparison.
        Null hypothesis: Strategy does NOT outperform the benchmark.
        """
        # A basic t-test for the mean of the difference (excess returns)
        excess = strategy_returns - benchmark_returns
        t_stat, p_val = stats.ttest_1samp(excess, popmean=0.0, alternative='greater')

        return {
            "t_stat": t_stat,
            "p_value": p_val,
            "reject_null": p_val < 0.05
        }

    @staticmethod
    def combinatorial_purged_cv(data_length: int, n_splits: int = 5, n_test_splits: int = 2, purge_length: int = 5) -> list:
        """
        Combinatorial Purged Cross-Validation (CPCV).
        Partitions historical dataset into non-overlapping training and validation windows,
        purging boundary data to avoid information leakage.

        Returns a list of tuples: [(train_indices, test_indices), ...]
        """
        # Basic implementation of standard purged CV
        # Split data into n_splits equally sized blocks
        indices = np.arange(data_length)
        block_size = data_length // n_splits
        blocks = [indices[i*block_size : (i+1)*block_size] for i in range(n_splits)]

        import itertools
        # All combinations of n_test_splits blocks
        test_combinations = list(itertools.combinations(range(n_splits), n_test_splits))

        splits = []
        for test_idx_tuple in test_combinations:
            test_indices = np.concatenate([blocks[i] for i in test_idx_tuple])
            train_indices = []

            for i in range(n_splits):
                if i not in test_idx_tuple:
                    train_block = blocks[i].copy()

                    # Purge logic: remove data points near test blocks
                    # If this block is immediately before a test block, purge the end
                    if (i + 1) in test_idx_tuple:
                        train_block = train_block[:-purge_length]
                    # If this block is immediately after a test block, purge the start
                    if (i - 1) in test_idx_tuple:
                        train_block = train_block[purge_length:]

                    train_indices.extend(train_block)

            splits.append((np.array(train_indices), test_indices))

        return splits
