# Cycle 3 — Comprehensive Check (Phase A5, gate-breaker standard Q25)

**Date:** 2026-08-16 (drafted; refile-confirm due 2026-09-17 with verdict)
**Scope:** 8 layers (a–h), measured evidence, PASS/FAIL, severity-graded findings.
**Gate rule (Q25):** ANY HIGH-severity finding BLOCKS the cycle verdict until fixed.

---

## Layer (a) — Data

| Item | Evidence | Status |
|---|---|---|
| OHLCV universe | 501 CSV files in `market_data_2019_2026/ohlcv/` (incl. `instruments.csv`, `missing.csv` excluded by engines); SPY/equity 2019-01-02 start, yfinance source, adjusted close column present | PASS |
| Claim 2 instruments | 12 verified CSVs (10 equity 1910 rows, BTC-USD/ETH-USD 2776 rows), window 2019-01-01..2026-08-07, header `date,open,high,low,close,volume,source` | PASS |
| 13F filings | 1241 XMLs in `cache/13f/`, no t_rowe funds; 27 of 28 factor quarters computable (2026Q1/Q2 pending exit prices); partial-XML-coverage funds handled; `13f_issues` entries treated as zero-change (Appendix B) | PASS |
| 481-name snapshot | `cache/cycle3_13f_ticker_map.json` → 481 tickers (ticker_to_cusips empty — map built from name→ticker, CUSIP direct mapping not required for claims 1/3/4); frozen, reused across claims | PASS |
| Missing/coverage handling | Probe excluded; funds with 0 XMLs → zero-change; unmapped SHARED/OTHER discretion 2,506,657 ignored, SOLE 126,048 mapped, 546,740 unmapped ignored (Appendix B.1 13F) | PASS |
| Crypto data | yfinance BTC/ETH used (CCXT Appendix B reserved but unused — yfinance succeeded) | PASS |

Findings:
- **LOW** — `ticker_to_cusips` map is empty (0 entries). Not required by the pre-registered claims (decile factors use ticker-level close data), but the 13F accumulation claim's CUSIP map rule is satisfied via ticker-name resolution; verify before any future CUSIP-dependent analysis.

---

## Layer (b) — Engine

| Engine | Regression check | Result |
|---|---|---|
| 13F (`cycle3_13f_engine.py`) | 2019Q3 forensic recompute (n=439, top decile +0.4867, bottom +0.0828, accumulators TSLA 38.5M/PCG 5.9M) matches | PASS — genuine |
| Multi-asset (`cycle3_multiasset_engine.py`) | Hand 2024-01-05: 11 longs, gross +1.4465%, cost 0.0091% → net +1.4374% **now matches fixed engine exactly** | PASS (after fix) |
| Low-vol (`cycle3_lowvol_engine.py`) | Hand 2024-01-05: net +0.0519% (turnover 0) matches engine exactly | PASS |
| ML (`cycle3_ml_engine.py`) | Forward-return timing exact for AAPL/MSFT/JPM 2024-01-05; decile L/S + 10bps cost logic identical to verified low-vol | PASS |

Findings:
- **MEDIUM (RESOLVED)** — Return-timing bug in `cycle3_multiasset_engine.py`: `weekly_returns()` used `s.pct_change().reindex(rebal)` (a ONE-DAY return) plus an extra `.shift(-1)`, misaligning the portfolio by a full week (earned next week's Friday daily return instead of the held week's Friday-to-Friday return). Hand check caught it: engine reported −0.8718% vs correct +1.4374% for 2024-01-05. Fixed (timing only; strategy/costs/gates unchanged), re-run, hand regression now matches. Documented in engine `data_handling_log` "RETURN-TIMING FIX". **Lesson recorded to knowledge base (1b3ee051-bdf1-4c2e-a60f-ebcbbf9e2920).**
- **LOW** — Dead code `costs_log` (low-vol), unused `norm_class` import (13F), unused `ytr`/`yoos` (ML) — 4 ruff F401/F841 findings. Cosmetic, non-behavioral, intentionally NOT edited post-results (engine-frozen discipline); to be cleaned in a non-result-affecting pass.
- **LOW** — ML fits issued sklearn `X does not have valid feature names` warnings (fit with feature names, predict with numpy array). Non-fatal; feature alignment is positional and column order is fixed by XCOLS.

---

## Layer (c) — Evaluation

All 4 claims evaluated vs frozen pre-registered bar (no post-hoc doc edits; deltas written BEFORE first backtest; Appendix B per claim).

| Claim | Gates (measured) | Verdict |
|---|---|---|
| C1 13F | train +0.87%/q (sign True); OOS median −0.80%/q; Sharpe 0.24; maxDD −7.0%; CAGR +2.1%; null p95 +6.09% > OOS mean +0.64% → null FAIL | **FAIL** |
| C2 multi-asset (corrected) | train +0.20%/wk (sign True); OOS median +0.35%/wk; Sharpe 1.59; maxDD −11.8%; CAGR +22.4% net; null p95 +0.58% > OOS mean +0.41% → null FAIL | **FAIL** |
| C3 low-vol | train −0.36%/wk → sign gate FAILED (dead on arrival); OOS median −0.46%/wk; Sharpe −1.18; maxDD −67.6%; CAGR −29.7% | **FAIL** |
| C4 ML | train-consistency −0.14%/wk → FAIL; OOS median +0.23%/wk; Sharpe 0.94; maxDD −12.4%; CAGR +13.0%; null p95 +0.27% > OOS mean +0.25% → razor-thin FAIL | **FAIL** |

Findings:
- **LOW** — All four claims fail; closest is C2 (null only) and C4 (null razor-thin + train consistency). No HIGH/MEDIUM evaluation-process findings: pre-registration discipline held; verdicts recorded with full numbers in `docs/data/cycle3_*_evaluation.json`.

---

## Layer (d) — Paper plumbing

| Item | Evidence | Status |
|---|---|---|
| A-config baseline | `baseline_paper_track.py` + `docs/data/baseline_state.json`: 15-name equal-weight 1-of-4, rsi neutral, start 2026-08-14, portfolio $100/cash $100, monthly_value 2026-08: 100 | PASS (running) |
| TE tracker | `te_tracker.py` + `te_report.json`: limit 0.02, months [] , breaches [], status OK | PASS (accruing from 2026-09 per plan) |
| Sandbox | `sandbox.yml` (5-day sandbox day state machine) + `paper_trading_sandbox.py` | PASS |
| Recon | `run-logs/paper-duel-recon-001.md` — CI paper loop live (keys in GH secrets, paper endpoint forced) | PASS |

Findings: none. Paper plumbing is independent of the failed claims (Q21a); unaffected by cycle outcome.

---

## Layer (e) — Execution adapters

| Adapter | Evidence | Status |
|---|---|---|
| Alpaca | `src/execution/alpaca_broker.py`, `live_alpaca_executor.py` (staged mods present) | PASS (paper-gated; LIVE_TRADING_ENABLED=False) |
| CCXT/crypto | `ccxt_broker.py`, `live_crypto_executor.py` | PASS (paper-gated) |
| Gate | `.env.example`: `LIVE_TRADING_ENABLED=False`, `PAPER_TRADING_ENABLED=True` | PASS — fail-closed default |

Findings:
- **LOW** — `docs(paper): broker_capability gate pending implementation` (commit 66b93df). The capability matrix is documented-pending; live entry cannot proceed until this gate is implemented. Not blocking (no winner → no live entry).

---

## Layer (f) — Ops / tests

| Item | Evidence | Status |
|---|---|---|
| Test suite | `pytest tests/` → **141 passed, 1 skipped** in 95.6s (local, anaconda python) | PASS |
| CI | `.github/workflows/ci.yml`: pytest + bandit -r src/ -lll + ruff check src/ on push to main | PASS |
| Workflows | 8 workflows (ci, api_health, daily_research, generate_strategies, pages, paper_trade, sandbox, self_improvement) | PASS |
| Run logs | `run-logs/` validation logs + trials.jsonl present | PASS |

Findings:
- **LOW** — CI runs on Python 3.12; local engines run on anaconda 3.13 (pytest ran under 3.13 local, pycache shows both 3.11/3.13/3.14 artifacts). Version drift exists; cycle3 engines pinned to installed sklearn 1.6.1 (delta declared). Non-blocking for analysis (local), but note for CI reproducibility of any engine promoted later.

---

## Layer (g) — Security

| Item | Evidence | Status |
|---|---|---|
| Secret scan | `secretscan` on `WSB-Alpha-System-latest` (excl. node_modules/.git/.cache/.swarm/.opencode): **0 findings** across 998 files | PASS |
| .env hygiene | `.env.example` ships placeholders only; real keys expected in GH secrets (paper recon confirms) | PASS |
| Bandit | CI runs `bandit -r src/ -lll -c bandit.toml` on main | PASS |
| Discipline | Engine `.gitignore`/workflow review: no secret literals in cycle3 scripts or docs | PASS |

Findings: none.

---

## Layer (h) — Costs

| Item | Evidence | Status |
|---|---|---|
| 13F claim | 2×10 bps/quarter flat (both legs), declared pre-reg | PASS |
| Multi-asset | turnover-based 5 bps equity / 10 bps crypto per side; final rebalance excluded | PASS |
| Low-vol / ML | 10 bps/side turnover-based (both legs), declared consistent with Claim 2 | PASS |
| Cost accounting verified | Hand regression for C2 (cost 0.0091% on 16.7% turnover) and C3 (turnover 0) match engine exactly | PASS |

Findings:
- **LOW** — Cost model ignores market-impact/slippage beyond fixed bps and ignores borrow costs on short legs (low-vol/ML short decile). Declared and pre-registered; adequate for a fail-closed research gate, but note for Phase B live sizing if any claim later passes (none currently do).

---

## Summary / Gate disposition

- **PASS layers:** a (data), b (engine, post-fix), c (evaluation), d (paper), e (adapters), f (ops/tests), g (security), h (costs).
- **HIGH findings:** none. **MEDIUM:** 1 (return-timing bug) — **RESOLVED** (fixed + verified + logged). **LOW:** 6 (empty CUSIP map; 4 ruff cosmetics; ML feature-name warning; capability gate pending; Python version drift; impact/borrow cost model).
- **Gate (Q25):** no HIGH-severity finding → **cycle verdict NOT blocked.**
- **Cycle 3 verdict (Phase A6):** all 4 pre-registered claims FAIL their bars (fail-closed). No winner → no paper/live entry for a claim; A-config baseline paper track continues independently (Q21a). Losers frozen for the cycle; reopenable only via pre-registered deltas (Q28). Earliest possible pass end-2027 (structural). Verdict refresh 2026-09-17 may complete 2026Q1/Q2 13F and pending 2026 weeks.

**Follow-ups (LOW, non-blocking):** clean ruff cosmetics in a non-result pass; implement broker_capability gate before any future live entry; consider impact/borrow cost model if a claim approaches its bar.
