import asyncio
from concurrent.futures import ThreadPoolExecutor

class AsyncExecutor:
    def __init__(self, broker, max_workers=4):
        self.broker = broker
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def execute_signals_parallel(self, signals):
        import functools
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(self.executor, functools.partial(self.broker.place_order, **signal))
            for signal in signals
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)
