import unittest
import asyncio
from src.execution.async_executor import AsyncExecutor

class TestExecution(unittest.TestCase):
    def test_async_executor_runs(self):
        class MockBroker:
            def place_order(self, **kwargs):
                return {"status": "success"}

        broker = MockBroker()
        executor = AsyncExecutor(broker)

        signals = [{"symbol": "AAPL", "qty": 1, "side": "buy", "order_type": "market"}] * 5

        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(executor.execute_signals_parallel(signals))

        self.assertEqual(len(results), 5)
        for res in results:
            self.assertEqual(res["status"], "success")

if __name__ == '__main__':
    unittest.main()
