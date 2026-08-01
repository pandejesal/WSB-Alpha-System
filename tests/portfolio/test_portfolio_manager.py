import unittest
from portfolio.portfolio_manager import PortfolioManager

class TestPortfolioManager(unittest.TestCase):
    def test_allocation_scaling(self):
        pm = PortfolioManager(max_strategies=3, max_allocation_per_strategy_pct=0.6)

        # Add two strong strategies
        pm.register_strategy("S1", confidence_score=100) # Wants 60%
        pm.register_strategy("S2", confidence_score=100) # Wants 60%

        # Total wants 120%. Should scale down to 50% each.
        self.assertAlmostEqual(pm.active_strategies["S1"], 0.5)
        self.assertAlmostEqual(pm.active_strategies["S2"], 0.5)

        # Target dollar allocation for a $100 account
        dollar_alloc = pm.get_target_allocation("S1", 100.0)
        self.assertAlmostEqual(dollar_alloc, 50.0)

    def test_max_strategies(self):
        pm = PortfolioManager(max_strategies=1, max_allocation_per_strategy_pct=0.5)
        self.assertTrue(pm.register_strategy("S1", 50))
        self.assertFalse(pm.register_strategy("S2", 50))

if __name__ == '__main__':
    unittest.main()
