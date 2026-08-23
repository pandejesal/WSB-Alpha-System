# Improvement Regime — Formal Conclusion (2026-08-14, session 5)

Status: CLOSED by user decision ("Adopt 'no universal edge'"). This document
is the terminal record of the pre-registered improvement loop.

## Verdict
**"No universal edge exists in this framework" is formally adopted.**

## Evidence trail (all pre-registered before execution, zero post-hoc changes)
1. Claim under test (from /grilling, docs/data/claim...): confluence config
   `neutral conf=5 hold=20 stop=0 long gate=F` on mega-caps.
2. Laggard falsification (2026-08-14): FAIL. B OOS median excess -0.15% on
   2024-2026 (2024 -1.80%, 2025 +0.28%, 2026 +1.76%, 49.2% WR). Claim died.
   docs/data/laggard_test.json.
3. DCA scenario: improved config beats SPY DCA by only +$101.59 over 5.7y
   (~0.4%/yr, within noise); production config LOSES -$276.57. docs/data/dca_scenario.json.
4. Improvement rounds (4 rounds, 14 pre-registered theme-runs, 0 kept):
   - R1 (6 themes): RSI slope, volume-surge hard filter, GK-regime conf,
     cross-sectional rank, combinations — all FAIL. Volume surge was the only
     A-improving variant (+0.76%) but B FAIL.
   - Parallel R2a (2): MACD rollover exit FAIL; pure trend core = first-ever
     B co-gate PASS (+0.11%) but A -1.29% FAIL.
   - This session R2 (4): SPY-state conf FAIL; RV-quantile regimes FAIL badly;
     surge booster = second B PASS (+0.28%) but A -0.74% FAIL; liquidity floor
     measured NO-OP (never binds).
   - This session R3 (2): persistence-adaptive router FAIL (-0.90% A, -0.68% B);
     persistence floor FAIL (-0.87% A, -0.63% B). Both worse than base.
5. Structural finding (3 independent B passes, 0 A+B passes): confluence
   clears A only; trend/surge cores clear B only. Routing attempt to exploit
   this (R3-1) REFUTED the interpretation: surge-booster B gains did not live
   in oscillating windows.
6. persistence_60 refuted as a separator in either direction (R3-2 destroyed A).

## Cumulative statistics
- Theme-runs: 14 (R1 0/6, parallel R2a 0/2, R2 0/4, R3 0/2). Kept: 0.
- The single A-passing config (confluence) never passed B in any round.
- No config has ever cleared both gates simultaneously.

## What the conclusion does and does not say
- DOES say: within this framework (this signal stack, hold/stop/sizing rules,
  this data, these universes), no pre-registered single rule produces
  positive median excess return on both mega-caps and laggards OOS.
- DOES NOT say: no edge exists anywhere (different data, exits, sizing, or
  claim scopes are outside this regime's mandate).
- The mega-cap-only claim variant was NOT adopted; it would be a CLAIM CHANGE
  requiring its own pre-registration (user declined).

## Remaining artifacts / state
- Candidate config unchanged and now formally DEPRECATED as a universal claim:
  `neutral conf5 hold20 stop0 long gate=F`. It remains the best measured A-only
  config (A OOS med +0.07%, 3-of-4 bar years complete; bar unpassable until
  end-2027 by design).
- All results JSONs retained: round1/1b/2/2a/2b/3_results.json,
  laggard_test.json, dca_scenario.json; all pre-registration docs retained
  (round1/2/3_preregistration.md).