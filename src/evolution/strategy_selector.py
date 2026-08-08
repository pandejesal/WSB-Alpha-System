
import numpy as np


class ThompsonSampler:
    def __init__(self, strategies: list[dict]):
        self.strategies = {s['id']: {'alpha': s.get('alpha', 1), 'beta': s.get('beta', 1)}
                          for s in strategies}

    def select(self) -> str:
        samples = {}
        for sid, params in self.strategies.items():
            samples[sid] = np.random.beta(params['alpha'], params['beta'])
        return max(samples, key=samples.get)

    def update(self, strategy_id: str, success: bool):
        if success:
            self.strategies[strategy_id]['alpha'] += 1
        else:
            self.strategies[strategy_id]['beta'] += 1

    def get_expected_values(self) -> dict[str, float]:
        return {sid: p['alpha'] / (p['alpha'] + p['beta'])
                for sid, p in self.strategies.items()}
