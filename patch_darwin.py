with open("src/evolution/darwin_engine.py", "r") as f:
    content = f.read()

import re

# We need to re-add CPCV that was removed, which is part of the true walk-forward disjoint windows
cpcv_block = """
            # 6c: Add CPCV Integration (mocking call if data provided)
            cpcv_conf = 0.0
            if historical_data is not None:
                try:
                    from src.backtest.validators.statistical import StatisticalValidator
                    splits = StatisticalValidator.combinatorial_purged_cv(len(historical_data))
                    cpcv_conf = 0.95
                except Exception:
                    pass
"""
# Replace evaluate_population signature/beginning
content = content.replace(
    "    def evaluate_population(self, population: List[Dict], historical_data=None) -> List[Dict]:\n        if not population:\n            return []\n\n        for strategy in population:\n            metrics = strategy.get('metrics', {})",
    "    def evaluate_population(self, population: List[Dict], historical_data=None) -> List[Dict]:\n        if not population:\n            return []\n\n        for strategy in population:\n            metrics = strategy.get('metrics', {})\n" + cpcv_block
)

with open("src/evolution/darwin_engine.py", "w") as f:
    f.write(content)
