# Registry Schema (Layer 3)

Target: `strategies/registry.json` (dict with "strategies" list). Stage 04 emits
artifacts; integration into the live registry is a separate user-initiated step.

## metadata.json shape (match existing entries)
```json
{
  "id": "<family>_<concept>_v<n>",
  "name": "<Human-readable strategy name>",
  "family": "momentum|trend|mean_reversion|multi-factor|sentiment-overlay|ta-rules|xgboost-exits",
  "venue": "alpaca",
  "spec_file": "strategies/<id>.yaml",
  "gates_passed": "<n>/6",
  "rank": <next integer>,
  "status": "evaluated",
  "evaluated_at": "<YYYY-MM-DD>"
}
```

## strategy.yaml
Must validate against src/ops/strategy_registry.py validate_spec. Base the file
on the approved stage-01 brief: signal.entry prose + machine indicators block,
universe, lookback constraints, risk params consistent with _config/risk-policy.md.
Header comment must include:
`# paper-only artifact — live trading DISABLED by operator policy`

## gates_passed semantics
Count only gates from _config/edge-gates.md actually evidenced in the review
verdict (max 6). Never inflate; reviewer numbers are the source of truth.
