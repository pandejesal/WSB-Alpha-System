import pandas as pd
import numpy as np
from src.alpha.smc import SmartMoneyConcepts
from src.risk.position_sizing import PositionSizer
import src.execution.execution_wrapper as ew

def test_smc():
    df = pd.DataFrame({
        'open': [10, 11, 10, 12, 13],
        'high': [12, 12, 11, 15, 14],
        'low': [9, 10, 9, 11, 12],
        'close': [11, 10, 11, 14, 13]
    })
    res = SmartMoneyConcepts.identify_fvgs(df)
    assert 'fvg_bullish' in res.columns
    print("SMC OK")

def test_position_sizing():
    qty = PositionSizer.calculate_position_size(
        account_equity=100.0,
        current_price=10.0,
        stop_loss_price=9.0,
        win_rate=0.6,
        win_loss_ratio=1.5,
        confidence_score=0.8
    )
    print(f"Position Sizer QTY: {qty}")
    assert qty > 0

if __name__ == '__main__':
    test_smc()
    test_position_sizing()
