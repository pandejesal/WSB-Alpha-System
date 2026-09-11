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

    def test_kelly_sizing_dual_constraint(self):
        pm = PortfolioManager(max_strategies=1, max_allocation_per_strategy_pct=0.5)
        pm.register_strategy("S1", confidence_score=100)
        for ret in (0.02, 0.03, 0.01):
            pm.kelly_sizer.record_trade({"return": ret})
        target = pm.get_target_allocation("S1", 100.0, trade_features={})
        # Kelly amount = 100 * 0.20 = 20 < confidence base 50 -> dual constraint picks 20
        self.assertAlmostEqual(target, 20.0)

    def test_kelly_fail_closed_no_history(self):
        pm = PortfolioManager(max_strategies=1, max_allocation_per_strategy_pct=0.5)
        pm.register_strategy("S1", confidence_score=100)
        target = pm.get_target_allocation("S1", 100.0, trade_features={})
        self.assertEqual(target, 0.0)

    def test_kelly_fail_closed_degenerate_inputs(self):
        pm = PortfolioManager(max_strategies=1, max_allocation_per_strategy_pct=0.5)
        # zero variance -> degenerate -> 0.0
        self.assertEqual(pm.kelly_sizer.kelly_size(0.05, 0.0), 0.0)
        # edge below min_edge -> 0.0
        self.assertEqual(pm.kelly_sizer.kelly_size(0.005, 0.1), 0.0)

    def test_compute_trade_risk_and_budget(self):
        pm = PortfolioManager(max_strategies=1, max_allocation_per_strategy_pct=0.5)
        risk = pm.compute_trade_risk(100.0, 99.0, 0.2)
        self.assertAlmostEqual(risk, 0.20)
        self.assertTrue(pm.check_risk_budget(100.0, risk))
        self.assertFalse(pm.check_risk_budget(100.0, 3.0))
