import unittest
import time
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.utils.gemini_client import RateLimiter
from src.research.agents.workflow import ResearchWorkflow
from src.evolution.darwin_engine import DarwinEngine

class TestPhase4(unittest.TestCase):

    def test_rate_limiter_delay(self):
        # Flash Lite: 15 RPM, min delay 4.5s
        limiter = RateLimiter(rpm_limit=15, rpd_limit=450, min_delay_sec=0.5) # Using 0.5s for fast testing instead of 4.5

        start = time.time()
        limiter.wait_if_needed()
        limiter.record_call()

        limiter.wait_if_needed()
        limiter.record_call()
        end = time.time()

        elapsed = end - start
        self.assertGreaterEqual(elapsed, 0.5, "Rate limiter did not enforce minimum delay")

    def test_langgraph_reflection_loop(self):
        # We can't easily mock the entire LLM for the full graph without extensive setup,
        # but we can test the reflection router logic
        workflow = ResearchWorkflow()

        state_fail = {
            "validation_passed": False,
            "reflection_count": 0
        }
        next_node = workflow.route_reflection(state_fail)
        self.assertEqual(next_node, "retry")

        state_max_retry = {
            "validation_passed": False,
            "reflection_count": 3
        }
        next_node_end = workflow.route_reflection(state_max_retry)
        self.assertEqual(next_node_end, "end")

        state_pass = {
            "validation_passed": True,
            "reflection_count": 1
        }
        next_node_pass = workflow.route_reflection(state_pass)
        self.assertEqual(next_node_pass, "end")

    def test_darwinian_fitness_and_selection(self):
        engine = DarwinEngine()

        population = [
            {"id": "strat1", "metrics": {"sharpe": 2.5, "win_rate": 0.60, "max_drawdown": 0.05}}, # High performer
            {"id": "strat2", "metrics": {"sharpe": 1.5, "win_rate": 0.50, "max_drawdown": 0.10}}, # Mid performer
            {"id": "strat3", "metrics": {"sharpe": 1.0, "win_rate": 0.45, "max_drawdown": 0.15}}, # Mid performer
            {"id": "strat4", "metrics": {"sharpe": -0.5, "win_rate": 0.30, "max_drawdown": 0.40}} # Terrible performer
        ]

        evaluated = engine.evaluate_population(population)

        # Check sorting (strat1 should be first, strat4 last)
        self.assertEqual(evaluated[0]["id"], "strat1")
        self.assertEqual(evaluated[-1]["id"], "strat4")

        # Check statuses
        self.assertEqual(evaluated[0]["status"], "promoted")
        self.assertEqual(evaluated[-1]["status"], "discarded")

        # Check mutation
        spec = {"parameters": {"rsi_period": 14, "threshold": 0.5}}
        mutated = engine.mutate_parameters(spec)
        self.assertNotEqual(mutated["parameters"]["rsi_period"], 14)
        self.assertIsInstance(mutated["parameters"]["rsi_period"], int)

if __name__ == '__main__':
    unittest.main()
