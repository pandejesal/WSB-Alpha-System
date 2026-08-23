# Workspace Setup Questionnaire (run once, or when policy changes)

Answer these to (re)configure the factory. Defaults shown come from the current
WSB-Alpha spec; confirm or override each.

1. Universe scope for new hypotheses?
   [default: 100-stock liquid large-cap panel excl. SPY/QQQ/AGG/BND; crypto
   (BTC/ETH) allowed per config/universe.json with 24/7 session + freshness gates]
2. Risk appetite — confirm hard caps? (see _config/risk-policy.md)
   [default: 1% risk/trade, 25% position, 4 concurrent, 5% daily CB, 15% DD CB]
3. Edge-gate thresholds — confirm? (see _config/edge-gates.md)
   [default: IS p<=0.05, CPCV, WF positive, permutation survival, DSR > 0]
4. Live trading stance?
   [default: DISABLED, paper only; flip only via live_gate_flip.yml human gate]
5. Cadence: max concurrent runs of this pipeline?
   [default: 1 run at a time; strict gates make parallelism counterproductive]
6. Naming: confirm candidate-id and run-slug conventions in risk-policy.md?
7. Write-back: confirm dual-layer memory policy (vault narrative + Mnemosyne
   atomic facts)? Any topics that must NOT be stored?
8. Kill-criteria defaults acceptable?

Record answers by editing _config/risk-policy.md and _config/edge-gates.md.
This file itself is the interview script, not a config store.
