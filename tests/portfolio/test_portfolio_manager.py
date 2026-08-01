import unittest
from src.risk.portfolio_manager import PortfolioManager

class TestPortfolioManager(unittest.TestCase):
    def test_allocation_scaling(self):
        pm = PortfolioManager(max_strategies=3, max_allocation_per_strategy_pct=0.6)
        pm.register_strategy("S1", confidence_score=100)
        pm.register_strategy("S2", confidence_score=100)
        self.assertAlmostEqual(pm.active_strategies["S1"], 0.5)
        self.assertAlmostEqual(pm.active_strategies["S2"], 0.5)
        dollar_alloc = pm.get_target_allocation("S1", 100.0)
        self.assertAlmostEqual(dollar_alloc, 50.0)

    def test_max_strategies(self):
        pm = PortfolioManager(max_strategies=1, max_allocation_per_strategy_pct=0.5)
        self.assertTrue(pm.register_strategy("S1", 50))
        self.assertFalse(pm.register_strategy("S2", 50))
