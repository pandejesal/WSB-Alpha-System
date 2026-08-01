from src.alpha.schemas import StrategySpecification

class PythonGenerator:
    def __init__(self):
        pass

    def generate(self, spec: StrategySpecification) -> str:
        """
        Translates a strict JSON StrategySpecification into executable Python code
        that fits into the BacktestEngine standard interface.
        """
        # Template for generating vectorbt compatible code or standard pandas loop code.
        # This acts as the scaffold for the LLM or template engine.

        params_str = ",\n        ".join(
            [f"{p.name}: {p.type} = {repr(p.default)}" for p in spec.parameters]
        )

        code = f"""
import pandas as pd
import numpy as np

class GeneratedStrategy_{spec.id.replace('-', '_')}:
    \"\"\"
    {spec.name}
    {spec.description}
    \"\"\"

    def __init__(self, {params_str}):
        # Initialize tunable parameters
"""
        for p in spec.parameters:
            code += f"        self.{p.name} = {p.name}\n"

        code += """
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        \"\"\"
        Compute indicators and generate entry/exit signals.
        Expects a DataFrame with OHLCV data.
        Returns the DataFrame with a 'signal' column (1 for long, -1 for short, 0 for flat).
        \"\"\"
        signals = pd.Series(0, index=df.index)

        # NOTE: Indicator computation logic would be dynamically injected here
        # based on spec.entry_conditions.

        df['signal'] = signals
        return df
"""
        return code
