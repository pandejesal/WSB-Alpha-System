import unittest
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.alpha.adapter import BaseStrategy as AdapterBaseStrategy, list_strategies, get_strategy


class TestFadeStrategyInheritance(unittest.TestCase):
    """Verify that FadeStrategy (and all private strategies) are interface-compatible
    with the adapter's BaseStrategy."""

    def test_adapter_base_strategy_interface(self):
        """Adapter's BaseStrategy defines the required abstract interface."""
        self.assertTrue(hasattr(AdapterBaseStrategy, 'generate_signals'))
        self.assertTrue(hasattr(AdapterBaseStrategy, 'get_name'))

    def test_strategies_base_strategy_interface(self):
        """Private strategies' BaseStrategy defines the same interface."""
        try:
            from strategies.src.alpha.base_strategy import BaseStrategy as StrategiesBaseStrategy
        except ImportError:
            from alpha.base_strategy import BaseStrategy as StrategiesBaseStrategy

        self.assertTrue(hasattr(StrategiesBaseStrategy, 'generate_signals'))
        self.assertTrue(hasattr(StrategiesBaseStrategy, 'get_name'))

    def test_fade_strategy_inherits_generate_signals(self):
        """FadeStrategy implements generate_signals from its BaseStrategy."""
        from strategies.src.alpha.fade_strategy import FadeStrategy
        self.assertTrue(hasattr(FadeStrategy, 'generate_signals'))
        # Verify it's not abstract (can be instantiated)
        fs = FadeStrategy()
        self.assertTrue(callable(fs.generate_signals))

    def test_fade_strategy_loads_via_adapter(self):
        """FadeStrategy is discoverable through the adapter's strategy registry."""
        strategies = list_strategies()
        # FadeStrategy may or may not be in the registry depending on __all__,
        # but if it is, it should be an instance with generate_signals.
        if 'FadeStrategy' in strategies:
            s = get_strategy('FadeStrategy')
            self.assertIsNotNone(s)
            self.assertTrue(hasattr(s, 'generate_signals'))

    def test_fade_strategy_generate_signals(self):
        """FadeStrategy's generate_signals produces a signal column."""
        from strategies.src.alpha.fade_strategy import FadeStrategy

        np.random.seed(42)
        dates = pd.date_range("2023-01-01", periods=50)
        df = pd.DataFrame({
            "Open": np.random.uniform(100, 110, 50),
            "High": np.random.uniform(110, 120, 50),
            "Low": np.random.uniform(90, 100, 50),
            "Close": np.random.uniform(100, 110, 50),
            "HA_Close": np.random.uniform(100, 110, 50),
            "HA_Open": np.random.uniform(100, 110, 50),
            "MACD": np.random.uniform(-1, 1, 50),
            "MACD_Signal": np.random.uniform(-1, 1, 50),
        }, index=dates)

        fs = FadeStrategy()
        result = fs.generate_signals(df)
        self.assertIn('signal', result.columns)
        self.assertTrue((result['signal'].isin([-1, 0, 1])).all())

    def test_all_strategies_interface_compatible(self):
        """Every loaded strategy has generate_signals and get_name."""
        strategies = list_strategies()
        for name in strategies:
            s = get_strategy(name)
            self.assertIsNotNone(s, f"Strategy {name} returned None")
            self.assertTrue(hasattr(s, 'generate_signals'),
                            f"{name} missing generate_signals")
            self.assertTrue(callable(s.generate_signals),
                            f"{name}.generate_signals not callable")


if __name__ == '__main__':
    unittest.main()
