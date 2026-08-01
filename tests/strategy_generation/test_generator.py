import unittest
from strategy_generation.schemas import StrategySpecification, Parameter
from strategy_generation.generator import PythonGenerator

class TestGenerator(unittest.TestCase):
    def test_python_generation(self):
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
