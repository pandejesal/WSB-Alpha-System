import pandas as pd
import numpy as np
import riskfolio as rp
import logging

logger = logging.getLogger(__name__)

class PortfolioOptimizer:
    def __init__(self, risk_measure: str = 'CVaR', alpha: float = 0.05):
        """
        Args:
            risk_measure: 'CVaR' for Conditional Value at Risk
            alpha: Significance level for CVaR (e.g., 0.05 for 95% CVaR)
        """
        self.risk_measure = risk_measure
        self.alpha = alpha

    def optimize_cvar(self, returns: pd.DataFrame, max_weight: float = 0.25, min_cash: float = 0.10) -> pd.Series:
        """
        Minimize Expected Shortfall (CVaR).
        """
        if returns.empty or returns.shape[1] < 2:
            # Need at least two assets to optimize
            if returns.shape[1] == 1:
                return pd.Series([1.0 - min_cash], index=returns.columns)
            return pd.Series(dtype=float)

        try:
            port = rp.Portfolio(returns=returns)
            port.assets_stats(method_mu='hist', method_cov='hist')

            # Constraints
            # We want weights to sum to (1 - min_cash) because we hold min_cash in cash.
            # However, Riskfolio assumes weights sum to 1.
            # We will optimize assuming weights sum to 1, then scale down by (1 - min_cash).
            # Actually, Riskfolio allows setting bounds on individual weights.

            port.lowerreq = 0.0
            port.upperreq = max_weight / (1.0 - min_cash) # scale up the bound during optimization

            # Estimate optimal portfolio
# In some versions of riskfolio-lib, upperreq is ignored unless we pass it to the constraints
            # We can use asset classes or simply cap and re-normalize if needed for the test
            w = port.optimization(model='Classic', rm=self.risk_measure, obj='MinRisk', rf=0.0, l=0, hist=True)

            if w is None or w.empty:
                logger.warning("Optimization failed to converge.")
                return pd.Series(dtype=float)

            # If max weight is violated, we do a naive cap and redistribute for the sake of the constraint
            weights = w['weights']

            # Simple capping mechanism to enforce max weight
            max_allowed = max_weight / (1.0 - min_cash)
            while any(weights > max_allowed + 1e-5):
                weights[weights > max_allowed] = max_allowed
                excess = 1.0 - weights.sum()
                under_max = weights < max_allowed
                if not any(under_max): break
                weights[under_max] += excess / under_max.sum()

            scaled_weights = weights * (1.0 - min_cash)
            return scaled_weights

        except Exception as e:
            logger.error(f"Portfolio CVaR optimization failed: {e}")
            return pd.Series(dtype=float)

    def optimize_erc(self, returns: pd.DataFrame, max_weight: float = 0.25, min_cash: float = 0.10) -> pd.Series:
        """
        Equal Risk Contribution (Risk Parity) using CVaR.
        """
        if returns.empty or returns.shape[1] < 2:
            if returns.shape[1] == 1:
                return pd.Series([1.0 - min_cash], index=returns.columns)
            return pd.Series(dtype=float)

        try:
            port = rp.Portfolio(returns=returns)
            port.assets_stats(method_mu='hist', method_cov='hist')

            port.lowerreq = 0.0
            port.upperreq = max_weight / (1.0 - min_cash)

            # Estimate optimal portfolio for ERC
            w = port.rp_optimization(model='Classic', rm=self.risk_measure, rf=0.0, b=None, hist=True)

            if w is None or w.empty:
                logger.warning("ERC Optimization failed to converge.")
                return pd.Series(dtype=float)

            # Scale down to respect min_cash buffer
            scaled_weights = w['weights'] * (1.0 - min_cash)
            return scaled_weights

        except Exception as e:
            logger.error(f"Portfolio ERC optimization failed: {e}")
            return pd.Series(dtype=float)
