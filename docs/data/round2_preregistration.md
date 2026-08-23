# Round 2 Improvement Themes — Pre-registration (2026-08-14)

Status: PRE-REGISTERED. No theme may be implemented until this file records its
hypothesis, mechanism, protocol, and acceptance criteria. Any change to a theme
after seeing results = post-hoc rationalization = disqualification.

## Context (from Round 1, all recorded BEFORE this file was written)
- All 4 Round 1 themes FAILED. Candidate config unchanged:
  neutral conf5 hold20 stop0 long gate=F.
- Observed facts that motivated Round 2:
  1. Volume surge was the ONLY variant improving Universe A OOS median
     (+0.76% vs +0.07%) but as a hard filter it never fixed laggards.
  2. Mega-cap vs laggard divergence (A +0.07% vs B -0.15% on identical rules)
     suggests the edge axis is universe CHARACTERISTICS, not indicator tuning.
  3. GK-vol regime bands never fired (conf-6 window empty 7.6y) — regime
     thresholds must use regimes that actually VARY.

## Protocol (identical to Round 1)
1. Implement as pure filter/adder on the signal stack. No param fitting on OOS.
2. Run on Universe A (15 mega-caps): train 2019-2023, OOS judgment 2024-2026.
3. Run on Universe B (10 laggards): OOS median excess must be > 0 (co-gate).
4. Acceptance: A OOS median >= base A OOS median AND B OOS median > 0.
   Failing the co-gate kills the theme regardless of A performance.
5. Record PASS/FAIL in docs/data/round2_results.json. Keep only PASS themes
   (max 1 merged per round into the candidate config; subsequent rounds stack).

## Theme R2-1: SPY-200d-state-contingent confidence
- Hypothesis: in bear regimes (SPY below its 200d MA) confluence signals are
  mostly false noise; the base config weights the market trend as just one of
  six score items. Requiring higher confidence specifically in bear regimes
  removes the worst trades without the all-or-nothing spy_gate block.
- Mechanism: conf_req = 6 when SPY < SPY_200d, else 5. Same 6-item score stack,
  no other changes.
- Distinction from tested variants (anti-disguise): this is NOT spy_gate
  (which blocks ALL signals when SPY < 200d) and NOT the flat conf 5/6 grid;
  it is a single contingent-confidence rule.
- Expected: fewer OOS trades in 2025/2026 bear windows, better median on both A
  and B.

## Theme R2-2: Realized-vol quantile regimes (replaces dead GK bands)
- Hypothesis: R1-3 failed because GK bands never varied. Ticker-level realized
  vol (20d std of daily returns) DOES vary. High-vol regimes are where false
  signals cluster; requiring conf 6 there (conf 5 below the regime boundary)
  tightens entries where noise is highest.
- Mechanism: regime per ticker per bar: rv20 = std(returns, 20); regime HIGH if
  rv20 > its own 75th percentile computed on TRAIN window only (2019-2023,
  rolling expand/forward only — no OOS leakage); conf 6 in HIGH, conf 5 else.
- Distinction: regime boundary is derived from TRAIN data only and recomputed
  identically on both universes; uses a regime that provably varies.
- Expected: higher-quality entries in high-vol windows; B co-gate pass.

## Theme R2-3: Volume surge as confidence BOOSTER (revisit R1-2, not a filter)
- Hypothesis: R1-2 improved A (+0.76%) as a HARD filter but cut trade count
  94% (905 vs 12897 sigs). Surge information should TILT confidence, not veto
  entries: surge days may trade at conf 5, non-surge days require conf 6.
- Mechanism: conf_req = 5 if Volume > 1.5x rolling 20-bar mean else 6.
  Identical score stack otherwise. (Equivalent to surge = +1 score item.)
- Distinction from R1-2: R1-2 required surge for ANY signal (mask AND); R2-3
  only relaxes the confidence threshold on surge bars.
- Expected: keeps most of the trade flow, concentrates entry quality on
  accumulation days, B co-gate pass.

## Theme R2-4: Liquidity floor (universe-characteristic axis, fixed thresholds)
- Hypothesis: the A/B divergence is driven by tradable characteristics, not
  ticker names. Small/illiquid laggards are where execution reality (slippage,
  signal quality) is worst. A pre-specified liquidity floor, applied IDENTICALLY
  to both universes, is a legitimate rule (not survivorship-by-name).
- Mechanism: require 20d mean dollar volume >= $20M AND 20d mean close >= $5
  (both thresholds FIXED at pre-registration, never tuned on either universe).
  Tickers failing the floor are excluded from the sim on that day (rule is
  per-bar, so a ticker can be filtered in/out over time).
- Honesty note: the floor will exclude most of Universe A never (all 15 pass)
  and part of Universe B over time (e.g., BA/GE/IBM in some windows). The B
  co-gate is then computed on the REMAINING B trades — same rule, no per-universe
  tuning. If the claim only survives because the floor removed the losers, that
  FAILS the spirit: the floor's threshold must be justified BEFORE results, so
  we record the expectation that B retains >50% of its tickers under the floor.
- Expected: keeps A intact, lifts B by removing the least tradable names.

## Execution order (one round per session; Round 2 = 4 themes max)
Round 2a: R2-1 SPY-state conf + R2-2 RV-quantile regimes (confidence-axis pair).
Round 2b (next session): R2-3 surge booster + R2-4 liquidity floor.

## Kill rules (unchanged from Round 1)
- No post-hoc parameter changes. Variants evaluated exactly as written above.
- A theme whose mechanism turns out identical to a prior tested variant
  (measured, not assumed) is declared NO-OP/DUPLICATE and not re-scored.
- Any theme that requires per-universe or per-ticker-name tuning is
  disqualified immediately.

## Round 2a results (2026-08-14, this session; docs/data/round2_results.json)

| Variant | A oos med | vs base | B oos med | B co-gate | Verdict |
|---|---|---|---|---|---|
| base | +0.07% | — | -0.15% | — | — |
| R2-1 spy_state conf | +0.00% | slightly worse | -0.45% | FAIL | FAIL |
| R2-2 rv_quantile | -1.22% | much worse | -1.05% | FAIL | FAIL |

Notes: R2-1 flipped A 2026 from -1.74% to +1.14% (bear-conf worked in 2026) but
hurt 2025 and did not fix B. R2-2 badly worse on both universes; the train-75th
pct RV threshold marked too many OOS bars HIGH and conf-6 starved quality.
Cumulative: 0/10 variants kept (R1 0/6, parallel R2a 0/2, this R2a 0/2).

## Cross-session observation (parallel session, docs/data/round2a_results.json)
Pure trend core (Close>SMA50 & SMA50>SMA200 & SPY>SPY200, hold 20) is the ONLY
variant with a B co-gate PASS so far: B +0.11% median (2025 +1.45%, 2026 +2.06%,
50.8% WR) but A -1.29%. Signal core behaves OPPOSITELY per universe: confluence
suits mega-caps, pure trend suits laggards. No mechanism rescue without a
pre-registered hypothesis.

## Round 2b results (2026-08-14; docs/data/round2b_results.json)

| Variant | A oos med | vs base | B oos med | B co-gate | Verdict |
|---|---|---|---|---|---|
| base | +0.07% | — | -0.15% | — | — |
| R2-3 surge_boost | -0.74% | worse | **+0.28%** | **PASS** | FAIL (A) |
| R2-4 liquidity | +0.07% | identical (NO-OP) | -0.15% | FAIL | FAIL |
| R2-3+R2-4 | -0.74% | worse | +0.28% | PASS | FAIL (A) |

Notes: R2-4 floor never binds — all 15 mega-caps AND all 10 laggards always
satisfy $20M 20d dollar volume and $5 price (per-bar floor, identical rule both
universes); it is a NO-OP by measurement, not re-scored. R2-3 (surge as
confidence booster, NOT the R1-2 hard filter) produced the second-ever B pass.

## Round 2 overall verdict
My Round 2: 0/4 themes kept (r21 FAIL, r22 FAIL, r23 FAIL-on-A, r24 NO-OP).
Cumulative across all sessions: 0/12 theme-runs kept (R1 0/6, parallel R2a 0/2,
this R2 0/4). Candidate config unchanged.

## Confirmed structural finding (three independent B passes vs zero A+B passes)
Confluence stack (base) is the ONLY thing that clears the A gate; pure-trend and
surge-boosted cores are the ONLY things that clear the B gate. No single
pre-registered config has ever cleared BOTH. Implication for Round 3: any claim
must either (a) adapt the signal core to per-ticker characteristics measured
BEFORE entry (e.g., a trendiness/momentum-state rule choosing between cores —
must be pre-registered, no per-name tuning), or (b) accept that a universal edge
does not exist in this framework.


