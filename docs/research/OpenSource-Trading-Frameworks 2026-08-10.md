# Open-Source Backtesting Framework Landscape — 2026-08-10

- Campaign: WSB-Alpha-System (Session 1, Task 5 input — live-design broker/backtest stack)
- Purpose: choose a statistically-viable backtesting/validation layer (walk-forward, OOS,
  permutation gates) with realistic fills across equities / crypto / futures / forex / options.
- Method: primary sources only — GitHub API (stars, license, `pushed_at`, releases), official
  docs pages, official notebooks. Secondary journalism used only where flagged. All checks done
  live on 2026-08-10.
- Scope: 12 frameworks, 4 shortlisted (NautilusTrader, LEAN, VectorBT, pybroker).

---

## Verdict (TL;DR)

| Shortlist | Why it's here | Biggest caveat |
|---|---|---|
| **NautilusTrader** | Best fill realism (L2/L3 orderbook), multi-market, most active core | No built-in walk-forward/optimizer (you assemble loops); single-threaded core |
| **LEAN (QuantConnect)** | Only one with **official** walk-forward-optimization docs; options/futures/forex/crypto all covered | Heavy C# core; local data licensing friction; cloud-centric workflows |
| **VectorBT** | Fastest research sweeps; official walk-forward example notebook; v1.1.0 (Jul 2026) | **Commons Clause license — no resale**; vectorized fills overstate fills on illiquid names; no options |
| **pybroker** | Easiest **built-in** walk-forward + bootstrap CIs; ML-trading focus; very active (pushed 2026-08-10) | Young project (~2019), smaller docs/community; custom license |

Recommendation shape: **VectorBT (or pybroker) for the research/parameter-sweep layer →
NautilusTrader as the realistic validation + paper/live execution layer**, with statistical
gates (permutation / DSR / PBO) applied on top via ecosystem tooling (see Validation section).

---

## Framework table (verified 2026-08-10)

Stars/activity = GitHub API at research time. License file read where it matters.

| Framework | Repo | ★ | License | Core | Engine | Markets | Fill realism | Walk-forward / OOS | Activity (push date) |
|---|---|---|---|---|---|---|---|---|---|
| NautilusTrader | nautechsystems/nautilus_trader | 25.4k | LGPL-3.0 | Rust core + Python | event-driven | equities, crypto, futures, forex, options (IB/Databento/Tardis adapters) | **highest** — L2/L3 orderbook, partial fills, slippage models | none built-in (official discussions: assemble via BacktestEngine/BacktestNode; #912, #3736) | 2026-08-10 |
| LEAN | QuantConnect/Lean | 21.1k | Apache-2.0 | C# + Python | event-driven | equities, options, futures, forex, crypto, CFD | configurable fill models (official docs) | **built-in pattern**, official docs page (incl. look-ahead-bias warning) | 2026-08-10 |
| VectorBT | polakowo/vectorbt | 8.6k | Apache-2.0 **+ Commons Clause** | Python/Numba (vectorized) | vectorized | any OHLCV (crypto, equities, futures); no options | next-bar fills + slippage/commission config; no intrabar/orderbook | official example notebook `WalkForwardOptimization.ipynb` | 2026-08-02 (release v1.1.0 2026-07-05, Python 3.14/pandas 3 support) |
| backtesting.py | kernc/backtesting.py | 8.8k | AGPL-3.0 | Python | event loop on OHLC bars | equities, crypto, forex, futures (any OHLCV) | limit/stop/SL/TP + shorting; intrabar checks; next-open fills; no partial fills | none built-in | 2026-08-05 |
| pybroker | edtechre/pybroker | 3.5k | custom (NOASSERTION) | Python/Numba | vectorized + bar callbacks | equities, ETFs, crypto | configurable slippage/fees; no orderbook | **built-in** `walkforward()` + bootstrap metric CIs (docs "Training a Model" notebook) | 2026-08-10 |
| Qlib | microsoft/qlib | 47.3k | MIT | Python | ML platform + vectorized portfolio sim (RosiC) | A-share default; US via external data | commission/slippage modeled in NestedExecutor | **built-in** Rolling (RollingStrategy) = rolling retrain walk-forward | 2026-07-23 |
| freqtrade | freqtrade/freqtrade | 53.1k | GPL-3.0 | Python | event-driven bot | crypto only | OHLCV fills at next candle open, fees, no limit simulation (docs "Assumptions made by backtesting"); lookahead-analysis + recursive analysis tools | no built-in WF (hyperopt for params) | 2026-08-10 |
| hftbacktest | nkaz001/hftbacktest | 4.3k | MIT | Rust + Python | event-driven tick/orderbook | crypto perps (Binance/Bybit data) | **highest** in niche — queue-position models (SquareProb...), L2/L3, latency modeling | none (HFT domain) | 2025-12-23 |
| bt | pmorissette/bt | 3.0k | MIT | Python | vectorized portfolio-level | any time series (equities/ETFs typical) | **none** — position/allocation-level, not trade-level | none built-in | 2026-08-07 |
| zipline-reloaded | stefan-jansen/zipline-reloaded | 1.9k | Apache-2.0 | Python | event-driven | US equities (factor research) | slippage models (e.g. volume-share), next-open fills | none built-in | 2026-01-06 (release 3.1.1, 2025-07-23) |
| backtrader | mementum/backtrader | 22.8k | GPL-3.0 | Python | event-driven | equities, crypto, futures, forex via feeds; no native options | next-open default, configurable slippage/commissions | none built-in (community examples only) | **last push 2024-08-19; no GitHub releases; last PyPI 1.9.78.123 (2023-11-07)** → long-term maintenance mode (secondary source S13) |
| QSTrader | quantstart/qstrader | 0.1k | MIT | Python | event-driven | equities | basic | none | **dead since 2019-03-08** — listed only to show the exclusion bar |

Excluded by maturity gate: PolarBT (nikkisora — young, few tests), quantbt (BobbyAxerol —
2026 launch, single author), backtesting-engine (danredelien — nautilus-based WFO, single author).
Keep on watchlist; re-check in 6 months.

---

## Validation / statistical-gate options per stack

- **pybroker**: `walkforward()` + bootstrap confidence intervals built in → fastest route to
  walk-forward + OOS gates with zero glue code.
- **Qlib**: `RollingStrategy` = rolling-retrain walk-forward, production-grade (MIT).
- **LEAN**: official Walk Forward Optimization doc — the only first-party WFO implementation.
- **VectorBT**: official `WalkForwardOptimization.ipynb` example (research-stage sweeps).
- **NautilusTrader**: no WFO — but `BacktestNode` runs independent time-window backtests in
  parallel processes; combine with Optuna/permutation harness externally (official discussions).
- **Ecosystem add-on (any framework)**: [backtest-audit](https://github.com/Aliipou/backtest-audit)
  — Deflated Sharpe Ratio, Probability of Backtest Overfitting, Monte-Carlo permutation,
  walk-forward OOS audit. Directly matches the campaign's perm-test gate (current p 0.11 IS /
  0.215 WF vs gates 0.01/0.05).

---

## License traps (matter for a commercial aim)

- **VectorBT**: Apache-2.0 **+ Commons Clause** — the additional clause forbids *selling* the
  software or services built on it. Read `LICENSE.md` before building any product around it.
- **backtesting.py**: AGPL-3.0 — network copyleft; fine for internal tooling, problematic if the
  system ever serves third parties.
- **backtrader / freqtrade**: GPL-3.0 — same copyleft consideration.
- Clean for commercial use: NautilusTrader (LGPL), LEAN (Apache-2.0), Qlib (MIT), hftbacktest
  (MIT), bt (MIT), zipline-reloaded (Apache-2.0).

---

## Fill-model realism ranking (full spectrum)

1. hftbacktest — tick-level orderbook + queue model + latency (crypto only)
2. NautilusTrader — L2/L3 orderbook, partial fills, slippage models (all markets via adapters)
3. LEAN — configurable fill models, options specifics
4. backtesting.py — intrabar limit/stop logic but no partial fills
5. zipline-reloaded — volume-share slippage proxies
6. VectorBT / Qlib / freqtrade — bar-level fills with fee/slippage params
7. bt — no fills modeled at all (portfolio-allocation level)

---

## Sources (all verified live 2026-08-10)

1. https://github.com/nautechsystems/nautilus_trader
2. https://github.com/QuantConnect/Lean
3. https://www.quantconnect.com/docs/v2/writing-algorithms/optimization/walk-forward-optimization
4. https://github.com/polakowo/vectorbt (LICENSE.md: Commons Clause)
5. https://nbviewer.org/github/polakowo/vectorbt/blob/master/examples/WalkForwardOptimization.ipynb
6. https://github.com/kernc/backtesting.py (+ API docs)
7. https://github.com/edtechre/pybroker
8. https://github.com/edtechre/pybroker/blob/master/notebooks/Training%20a%20Model.ipynb
9. https://github.com/microsoft/qlib
10. https://www.freqtrade.io/en/stable/backtesting/ (assumptions section)
11. https://github.com/nkaz001/hftbacktest
12. https://hftbacktest.readthedocs.io/en/latest/tutorials/Probability%20Queue%20Models.html
13. https://www.aifinhub.com/articles/4836545121930125851 (BullAlert 2026-05-26; backtrader maintenance-mode claim only)
14. https://nautilustrader.io/docs/latest/integrations/ib/
15. https://github.com/nautechsystems/nautilus_trader/discussions/912
16. https://github.com/nautechsystems/nautilus_trader/discussions/3736
17. https://github.com/stefan-jansen/zipline-reloaded
18. https://github.com/pmorissette/bt
19. https://github.com/mementum/backtrader ; https://pypi.org/project/backtrader/
20. https://github.com/quantstart/qstrader
21. https://github.com/Aliipou/backtest-audit
22. https://qlib.readthedocs.io/en/latest/docs/component/backtest.html
23. https://github.com/nikkisora/PolarBT ; https://github.com/BobbyAxerol/quantbt ; https://github.com/danredelien/backtesting-engine

## Open questions / next

- Verify current viability numbers by running the repo's permutation + walk-forward scripts (Task 3.1) — decide stack after that.
- Decide framework pick as Decision note; tie into Task 5 live-design (broker abstraction: Alpaca/IB/CCXT) — Nautilus covers IB adapters natively.