# Lean Engine Port — Local CSV Backtest

Minimal Python port of QuantConnect Lean's core API, using local CSV data files. No network calls, no API keys.

## Key Differences from Lean

| Concept | Lean | Port |
|---|---|---|
| Data feed | Live/S3/ObjectStore | Local CSV only |
| Fill model | Market/Limit/Stop | Next-bar close (T+1) |
| Fee model | BrokerageFeeModel | Per-share flat ($0 default) |
| Slippage | SlippageModels | BPS of fill price ($0 default) |
| Benchmark | Internal | SPY buy-hold |
| Scheduling | TimeRules/DateRules | Simple date list |
| Universe | Active selection | All CSVs in directory |

## Mapping Table

| Lean | Port | Notes |
|---|---|---|
| `QCAlgorithm` | `Algorithm` | Base class, same lifecycle |
| `Initialize()` | `Initialize()` | Set up cash, dates, benchmark |
| `OnData(Slice)` | `OnData(Slice)` | Called each bar |
| `AddEquity(sym)` | `AddEquity(sym)` | Loads CSV from csv_root |
| `SetCash(n)` | `SetCash(n)` | Starting portfolio value |
| `SetStartDate(d)` | `SetStartDate(y,m,d)` | Backtest start |
| `SetEndDate(d)` | `SetEndDate(y,m,d)` | Backtest end |
| `SetBenchmark(sym)` | `SetBenchmark(sym)` | SPY buy-hold benchmark |
| `SetHoldings(sym, w)` | `SetHoldings(sym, w)` | Long-only, 0–100% |
| `Liquidate(sym)` | `Liquidate(sym)` | Close position at next bar open |
| `Schedule.On(...)` | Not implemented | Stub only |
| `self.Portfolio` | `self.Portfolio` | Holdings dict |
| `self.Debug(...)` | `self.Debug(...)` | Logs to list + print |
| `self.Log(...)` | `self.Log(...)` | Same as Debug |

## Data Format

The engine reads two CSV formats:

**Format A** (data/spy_ohlcv_2019_2026.csv):
```csv
Date,"('Close', 'SPY')","('High', 'SPY')","('Low', 'SPY')","('Open', 'SPY')","('Volume', 'SPY')"
```

**Format B** (market_data_2019_2026/ohlcv/SPY.csv):
```csv
date,open,high,low,close,volume,source
```

## Usage

```python
from src.backtest.lean_engine import Algorithm, Slice

class MyAlgo(Algorithm):
    def Initialize(self):
        self.SetCash(100_000)
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2025, 12, 31)
        self.SetBenchmark("SPY")
        self.AddEquity("SPY")

    def OnData(self, slice: Slice):
        if "SPY" in slice:
            self.SetHoldings("SPY", 1.0)

algo = MyAlgo()
results = algo.run()
print(results["strategy_return"])
```

## Results Dict

```python
{
    "strategy_return": 0.1698,       # decimal (verified 2026-09-04, Hermes re-run)
    "benchmark_return": 2.0308,      # decimal (SPY buy-hold, same window)
    "total_orders": 14,
    "total_fees": 0.0,
    "orders": [
        {
            "date": "2020-01-02",
            "symbol": "SPY",
            "quantity": 100,
            "fill_price": 325.0,
            "fee": 0.0,
            "slippage": 0.0,
            "reason": "SetHoldings",
        }
    ],
}
```

## Verification (2026-09-04, Hermes audit)

- `pytest tests/test_lean_port.py` — 16 passed (independently re-run).
- `ruff check` — clean. `bandit` — 0 medium/high.
- CLI re-run reproduced the worker's numbers exactly: strategy +16.98%
  vs SPY benchmark +203.08%, 14 orders, $0 fees (Alpaca-compatible
  flat fee model), T+1 fills confirmed. This worker was the cleanest of
  the five — the only fix needed was replacing placeholder numbers in
  this doc with the real run above.
- Verdict: engine plumbing verified (targets, fills, fees, benchmark,
  buying-power rejection). The demo SMA-cross itself trails SPY badly —
  expected for a naive cross. Status: paper research only.
