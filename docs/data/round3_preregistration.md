# Round 3 Improvement Themes — Pre-registration (2026-08-14, session 5)

Status: PRE-REGISTERED. No theme may be implemented until this file records its
hypothesis, mechanism, protocol, and acceptance criteria. Any change after
seeing results = post-hoc rationalization = disqualification.

## Established facts (all recorded in docs/data/round1_preregistration.md,
## round2_preregistration.md, round1/1b/2/2a/2b_results.json — BEFORE this file)
- Cumulative: 0/12 theme-runs kept across all sessions. Candidate config
  unchanged: neutral conf5 hold20 stop0 long gate=F (CONFLUENCE core).
- CONFIRMED STRUCTURAL FINDING (3 independent B passes, 0 A+B passes):
  * Confluence core (base) clears Universe A ONLY: A +0.07% OOS med, B -0.15%.
  * Pure trend core (Close>SMA50 & SMA50>SMA200 & SPY>SPY200, hold 20) clears
    Universe B ONLY: B +0.11% (2025 +1.45%, 2026 +2.06%), A -1.29%.
  * Surge booster (SAME confluence stack, conf 5 on surge bars / conf 6 else,
    surge = vol > 1.5x rolling-20 mean) clears Universe B ONLY:
    B +0.28% (2025 +2.28%, 2026 +0.57%, 50.8% WR, all 10 tickers traded),
    A -0.74%.
- Interpretation: mega-caps profit from broad confluence INCLUDING non-surge
  drift days; laggards lose on non-surge drift but win on volume-confirmed and
  persistent-trend windows. The distinguishing pre-entry characteristic is
  TREND PERSISTENCE, not ticker name: mega-caps mostly held Close>SMA_200
  structure 2019-2026; laggards mostly oscillated around SMA_200.

## Round 3 base definitions (identical to prior rounds)
- Universe A (15 mega-caps), Universe B (10 laggards); data market_data_2019_2026/ohlcv.
- Sim: T+1 fills, ATR slippage x1, 0.04% round-trip commission, max 4 positions
  equal weight, hold 20, stop 0, long only, gate=F, vol shield GK<1.2.
- Train 2019-2023 (selection), OOS judgment 2024-2026.
- Acceptance: A OOS median >= base A (+0.07%) AND B OOS median > 0 (co-gate).
  Record PASS/FAIL in docs/data/round3_results.json. Keep only PASS themes
  (max 1 merged per round; on a tie keep the SIMPLEST mechanism).

## New fixed parameter (zero free params in this round — all set NOW)
persistence_60(ticker, bar) = fraction of the trailing 60 bars (bar-59..bar,
inclusive, pre-entry data only) where Close > SMA_200.
- Split threshold for routing: P_ROUTE = 0.8
- Floor threshold for filtering: P_FLOOR = 0.6
- Window 60 bars fixed; both thresholds FIXED at pre-registration, never tuned,
  applied identically to both universes. No per-ticker-name logic anywhere.

## Theme R3-1: Persistence-adaptive core router
- Hypothesis: route each ticker to the core that its structure empirically
  supports: persistent-trend structure (persistence_60 >= 0.8) -> CONFLUENCE
  core (exact base); oscillating structure (persistence_60 < 0.8) -> SURGE
  BOOSTER core (exact R2-3: conf 5 on surge bars, conf 6 on non-surge bars,
  same confluence stack). One pre-specified rule clears both gates.
- Mechanism: per ticker per bar, compute persistence_60; choose core per bar
  (router is per-BAR, so a ticker can flip over time). All other sim rules
  identical.
- Distinction from tested variants: NOT a per-name split; NOT a blend; the
  router's two branches are EXACTLY the two already-measured cores, so the
  only new claim is the routing rule itself.
- Expected: A ~ base (mega-caps mostly persistent), B ~ surge booster
  (laggards mostly oscillating); both gates clear.

## Theme R3-2: Persistence floor (single core + filter)
- Hypothesis: the B losses come from entering oscillating names; filtering
  low-persistence bars (persistence_60 < 0.6 -> no signal) fixes B without
  touching A. Tests whether persistence ALONE (without core switching)
  explains the divergence. If R3-2 passes both gates, it is the simpler rule
  and wins any tie vs R3-1.
- Mechanism: CONFLUENCE core (exact base) + require persistence_60 >= 0.6 at
  the signal bar. Nothing else changes.
- Distinction: single core; the only change is the persistence filter.
- Expected: A ~ base; B improved by removing oscillating-window entries.

## Tie-break rule (pre-specified)
If both R3-1 and R3-2 PASS: keep the simpler mechanism (R3-2: one core +
one filter) unless R3-1's min(A,B) median exceeds R3-2's by >= 0.10pp, in
which case keep R3-1. If neither passes: 0/14 cumulative, candidate config
unchanged, Round 4 must pre-register new hypotheses or the conclusion
"no universal edge in this framework" is formally adopted.

## Kill rules (unchanged)
- No post-hoc parameter changes. Variants evaluated exactly as written.
- Measured NO-OP or DUPLICATE mechanisms are declared, not re-scored.
- Per-universe/per-name tuning disqualifies immediately.

## Round 3 results (2026-08-14; docs/data/round3_results.json)

| Variant | A oos med | vs base | B oos med | vs base | Verdict |
|---|---|---|---|---|---|
| base | +0.07% | — | -0.15% | — | — |
| R3-1 router | -0.90% | worse | -0.68% | worse | FAIL |
| R3-2 floor | -0.87% | worse | -0.63% | worse | FAIL |

Both FAIL, both WORSE than base on both universes. persistence_60 undefined
(first 59 bars) was fail-closed (no signal) as pre-registered.

Decisive observations:
1. R3-1 did NOT preserve R2-3's B edge (+0.28% -> -0.68%). The surge-booster
   branch (persistence < 0.8) routed EXACTLY like R2-3, so R2-3's B gains were
   NOT concentrated in oscillating windows: they lived in windows this router
   either handed to the confluence branch or removed via the fail-closed
   undefined window. The structural-finding interpretation ("oscillating
   laggards want the surge core") is REFUTED by routing on it.
2. R3-2 floor made A WORSE (-0.87%): on mega-caps the low-persistence
   (oscillating) bars were the profitable OOS entries. So persistence_60 is not
   a valid separator in either direction.

## Round 3 overall verdict
0/2 themes kept. Cumulative across all sessions: 0/14 theme-runs kept
(R1 0/6, parallel R2a 0/2, this R2 0/4, this R3 0/2). Candidate config
unchanged. Per pre-registration: "Round 4 must pre-register new hypotheses or
the conclusion 'no universal edge in this framework' is formally adopted."

## Standing evidence summary (as of Round 3)
- Falsification: laggard claim died (B OOS med -0.15%; 2024 -1.80%).
- 14 pre-registered variants, 0 kept. The only two B co-gate passes (pure
  trend +0.11%, surge booster +0.28%) both destroy A, and the routing attempt
  to exploit them destroyed B as well.
- The single measured A-passing config (confluence) has never passed B.
- The improvement regime has now been given 4 rounds. Formally adopting
  "no universal edge" is the pre-registered fallback; narrowing the claim to
  mega-caps-only is a CLAIM CHANGE requiring its own pre-registration.

