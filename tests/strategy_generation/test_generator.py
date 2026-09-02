import unittest
from src.alpha import get_strategy

# Lazy-load schemas and generator (from private repo)
try:
    from src.alpha.schemas import StrategySpecification, Parameter
    from src.alpha.generator import PythonGenerator
    HAS_PRIVATE = True
except ImportError:
    HAS_PRIVATE = False

class TestGenerator(unittest.TestCase):
    def test_python_generation(self):
        if not HAS_PRIVATE:
            self.skipTest("Private strategies repo not available")
        spec = StrategySpecification(
            id="1234-abcd",
            name="Test Strategy",
            description="Mean reversion",
            parameters=[
                Parameter(name="rsi_period", type="int", default=14)
            ]
        )
        generator = PythonGenerator()
        code = generator.generate(spec)

        self.assertIn("class GeneratedStrategy_1234_abcd:", code)
        self.assertIn("self.rsi_period = rsi_period", code)
        self.assertIn("def generate_signals", code)

if __name__ == '__main__':
    unittest.main()
