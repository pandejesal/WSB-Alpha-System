## Claim
buying the base signal (e.g., spy_sma200) ONLY when 5-day debate score > 0.0 raises net Sharpe vs the unfiltered signal without cutting trade count below 10

## Strategy Spec
```yaml
id: sentiment_overlay_sma_entry_v1
name: SPY SMA-200 with Sentiment Entry Filter
family: sentiment_overlay
venue: alpaca
universe: SPY (single liquid index ETF)
pre_registration_ref: "docs/data/cycle1_prereg_sentiment_overlay.md"
gates_passed: "0/5"
verdict: "PENDING"
eval_records: "docs/data/eval_sentiment_overlay.json"
signal:
  entry: "enter all-in SPY when SPY close > SMA(200) AND sentiment score > 0.0"
  exit: "exit to cash when SPY close < SMA(200)"
  sizing: "$100 account: full $100 in SPY when in market, 100% cash when flat"
  caps:
    max_concurrent_positions: 1
  rebalance: "daily target rows"
parameters:
  window: 200
  exec_delay: 1
  drift_rebal: 0.05
  sentiment_module: src.research.debate_engine
  sentiment_field: score
  sentiment_threshold: 0.0
  sentiment_mode: entry_filter
edge_gate_params:
  min_trade_count: 10
  sharpe_lift: 0.1
```
