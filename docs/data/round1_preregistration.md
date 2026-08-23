# Round 1 Improvement Themes — Pre-registration (2026-08-14)

Status: PRE-REGISTERED. No theme may be implemented until this file records its
hypothesis, mechanism, protocol, and acceptance criteria. Any change to a theme
after seeing results = post-hoc rationalization = disqualification.

Context: the honest claim (neutral conf5 hold20 stop0 long gate=F) died on the
laggard falsification test (median excess -0.15% on 2024-2026). Round 1 must
therefore target GENERALIZATION, not just mega-cap performance. Every theme is
tested on BOTH universes and must pass the laggard co-gate.

## Base configuration (unchanged during Round 1)
- Universe A (mega-caps, 15): AAPL MSFT GOOGL AMZN NVDA META TSLA JPM V JNJ WMT MA UNH XOM DIS
- Universe B (laggards, 10): INTC PFE KO BA T CSCO VZ MRK GE IBM
- Base: rsi=neutral conf=5 hold=20 stop=0 direction=long_only gate=F
- Sim: T+1 fills, ATR slippage (x1), 0.04% round-trip commission, max 4 positions equal-weight
- Train: 2019-2023 (selection), OOS judgment: 2024-2026
- Data: market_data_2019_2026/ohlcv (2019-01-02 -> 2026-08-07, 1910 bars/ticker)

## Protocol for each theme
1. Implement as a pure filter/adder on the signal stack (no param fitting on OOS).
2. Run on Universe A: report train + OOS (2024-2026) median excess, per-year.
3. Run on Universe B (laggards): report OOS median excess.
4. Acceptance: on Universe A, OOS median excess >= base OOS median (+1.5pp on mean excess
   preferred but not required); AND on Universe B OOS median excess > 0 (laggard co-gate).
   Failing the co-gate kills the theme regardless of A performance.
5. Record PASS/FAIL per theme in docs/data/round1_results.json. Keep only PASS themes
   (max 1 merged per round into the candidate config; subsequent rounds stack).

## Theme R1-1: RSI slope confirmation
- Hypothesis: flat RSI band (30-70) admits late entries into exhausted moves.
  An upward RSI_14 slope (RSI now > RSI 5 bars ago) filters early-strength
  entries and improves entry timing across BOTH mega-caps and laggards.
- Mechanism: long requires RSI > 30 AND RSI < 70 AND RSI > RSI.shift(5) (+1 score item,
  still gate=F, conf>=5). Short mirrored.
- Expected: fewer trades, higher median excess, laggard co-gate pass.

## Theme R1-2: Volume surge confirmation
- Hypothesis: confluence signals without volume confirmation enter on drift,
  not demand; requiring Volume > 1.5x rolling 20-bar mean on the signal bar
  concentrates entries into accumulation phases.
- Mechanism: +1 score item requiring volume surge on signal bar (long only mirror).
- Expected: fewer trades, higher win rate, laggard co-gate pass.

## Theme R1-3: GK-vol regime conditioning (regime-aware confidence)
- Hypothesis: the binary vol shield (GK_Vol < 1.2) is a blunt gate; elevated-vol
  regimes are where false signals cluster. Conditioning the CONFIDENCE THRESHOLD
  on GK vol (conf 6 when GK in [1.2, 1.5], conf 5 when GK < 1.2, no trades when
  GK >= 1.5) tightens entries where noise is highest without a full shutdown.
- Mechanism: per-bar dynamic min_conf, otherwise same score stack.
- Expected: higher quality entries in high-vol windows; laggard co-gate pass.

## Theme R1-4: Cross-sectional ranking (same-day, multi-ticker)
- Hypothesis: on days with multiple signals, the strongest relative momentum
  wins; taking signals in ticker order (as today) wastes slots on weak names.
- Mechanism: on each day, sort candidate signals by 20-day return (or RSI
  proximity), fill only the top MAX_POSITIONS by rank.
- Expected: same trade count, better median excess; laggard co-gate pass.

## Execution order (one round per session, max 2 themes per session for Round 1)
Round 1a: R1-1 RSI slope + R1-2 volume surge (filters, same framework).
Round 1b (next session): R1-3 GK regime conditioning + R1-4 cross-sectional ranking.

## Round 1a results (2026-08-14, recorded BEFORE any further work)
All variants FAIL the laggard co-gate -> none kept. Candidate config unchanged.

| Variant | A oos med | vs base | B oos med | B co-gate | Verdict |
|---|---|---|---|---|---|
| base | +0.07% | — | -0.15% | — | — |
| R1-1 rsi_slope | -0.90% | worse | -0.68% | FAIL | FAIL |
| R1-2 volume_surge | +0.76% | better | -0.16% | FAIL | FAIL |
| R1-1+R1-2 both | -0.01% | worse | -0.79% | FAIL | FAIL |

Notes: volume_surge improved A OOS median but did not fix B; rsi_slope hurt both.
Full numbers in docs/data/round1_results.json. Kill criteria honored: no post-hoc
parameter fiddling; variants evaluated exactly as pre-registered.

## Round 1b results (2026-08-14)

| Variant | A oos med | vs base | B oos med | B co-gate | Verdict |
|---|---|---|---|---|---|
| base | +0.07% | — | -0.15% | — | — |
| R1-3 gk_conf | +0.07% | identical (no-op) | -0.15% | FAIL | FAIL |
| R1-4 rank | -0.16% | worse | -0.82% | FAIL | FAIL |
| R1-3+R1-4 | -0.16% | worse | -0.82% | FAIL | FAIL |

Notes: R1-3 was a no-op — the conf-6 window (GK in [1.2,1.5) with all 6 score
items true) never fired in 7.6y of data; GK>=1.5 never occurred either. R1-4
ranking by 20-day return was actively harmful on both universes (momentum-ranked
slot filling picks names that mean-revert worse). Full numbers in
docs/data/round1b_results.json.

## Round 1 overall verdict (both sub-rounds)
All 4 pre-registered themes FAILED the laggard co-gate or degraded Universe A.
Candidate config unchanged: neutral conf5 hold20 stop0 long gate=F.
Round 2 (next session): must pre-register NEW hypotheses. Observed useful facts:
(1) volume surge was the only variant improving A OOS median (+0.76% vs +0.07%);
(2) mega-cap vs laggard divergence suggests universe conditioning, not indicator
tuning, may be the real axis; (3) the conf-6 regime window never fires — any
regime-conditioned threshold must use a regime that actually varies (e.g.,
SPY 200d trend state or realized-vol quantiles, not GK bands).


## Round 1b results (2026-08-14, same session; recorded before Round 2 pre-registration)

| Variant | A oos med | vs base | B oos med | B co-gate | Verdict |
|---|---|---|---|---|---|
| base | +0.07% | — | -0.15% | — | — |
| R1-3 gk_conf | +0.07% | identical (no-op) | -0.15% | FAIL | FAIL |
| R1-4 rank | -0.16% | worse | -0.82% | FAIL | FAIL |
| R1-3+R1-4 | -0.16% | worse | -0.82% | FAIL | FAIL |

R1-3 was a no-op: on both universes no bar had GK in [1.2,1.5) with score>=6 AND no
bar had GK>=1.5 with score>=5, so regime conditioning never changed a signal.
R1-4 (fill best 20-day-return first) made both universes worse — entry quality
ordering by recent momentum is not the fix.
Full numbers in docs/data/round1b_results.json.

## ROUND 1 CLOSED: 0/6 variants kept. Candidate config unchanged.

Learning: entry-side filters on a 6-item confluence score do not generalize to
laggards; the mega-cap OOS edge (tiny, +0.07% median) is not salvageable by
adding entry conditions. Round 2 must attack EXIT structure and SIGNAL CORE,
not add entry filters.


