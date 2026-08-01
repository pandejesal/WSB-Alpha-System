import pandas as pd
import numpy as np
from permutation_tester import PermutationValidator
from incubation_manager import StrategyStateManager

# Mock Strategy for testing
def mock_strategy_evaluator(df: pd.DataFrame) -> float:
    # Just returns a random profit factor for testing
    return np.random.uniform(0.5, 2.5)

if __name__ == '__main__':
    # Generate some dummy data
    dates = pd.date_range("2023-01-01", periods=100, freq="D")
    df = pd.DataFrame({
        "Open": np.random.randn(100) + 100,
        "High": np.random.randn(100) + 105,
        "Low": np.random.randn(100) + 95,
        "Close": np.random.randn(100) + 100,
        "Volume": np.random.randint(1000, 5000, 100)
    }, index=dates)

    tester = PermutationValidator(num_permutations=100)
    result = tester.validate(mock_strategy_evaluator, df)

    if result["status"] == "PASSED":
        manager = StrategyStateManager()
        manager.register_strategy("mock_strategy_passed")
        print("Strategy Registered in Incubation!")
    else:
        print("Strategy Rejected!")
