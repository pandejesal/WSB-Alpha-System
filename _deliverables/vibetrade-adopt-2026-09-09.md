# Vibe-Trading Adoption Study — Options-Backtest + Multi-Agent Patterns for VRP Sleeve (Paper-Only)

Date: 2026-09-09
Status: STUDY ONLY — no code changed. `evolve_real.py`, `strategies/registry.json`, `strategies/` untouched per task constraint. Workdir-contained.
Scope: adopt-study of upstream `HKUDS/Vibe-Trading` multi-agent framework — options backtesting (delta/IV surfaces, multi-leg fills), LLM agent reasoning + execution routing + risk limits. Assess fit for this repo: (a) options-backtest module patterns adaptable to a VRP (variance-risk-premium) sleeve, paper-only; (b) agent-orchestration patterns vs existing `src/research/debate_engine.py` + `src/research/alptrading_debate.py`. Explicit REJECT of live autonomous execution. Exact diffs + test plan.

Upstream sources read (fetched 2026-09-09):
- `agent/backtest/engines/options_portfolio.py` (v2 header + full `run_options_backtest`) — HV synth, `leg_iv` smile choke, multi-leg open/close/partial-close, next-close fills, margin + reject records, `greeks.csv`, expiry-after-fills.
- `agent/src/quantlib/options.py` — `bs_price` / `bs_greeks` / `implied_volatility` / `normalise_option_type`, degenerate-intrinsic handling, theta-per-day / vega-rho-per-1pp, Newton→brentq with `SIGMA_RESOLUTION` identifiability → `nan`.
- `agent/backtest/engines/base.py` (`BaseEngine`, `_align`, `evaluation_start_index`, optimizer hooks, artifacts) — truncated fetch, core loop + alignment + warm-up semantics confirmed via DeepWiki mirror.
- DeepWiki `4-backtesting-framework` + `5-swarm-intelligence` + `10-live-trading-system` (indexed e88db0f5): runner config-driven flow, `LOADER_REGISTRY`/`FALLBACK_CHAINS`, `SwarmRuntime` topological DAG + `ThreadPoolExecutor`, presets (`SwarmAgentSpec`/`SwarmTask`), grounding, DAG gating `blocked`, `report.md` contract, Mandate/Consent/`LiveOrderGuardTool` 6-step gate, kill-switch `HALT`, `audit.jsonl`.
- News/changelog note: `2026-09-01 — options backtests filled at the price the signal was computed from, naked short could sell premium it could never cover` → fixed to next-bar pricing + margin. This is the exact phantom-edge class this repo must not reintroduce.
- `agent/SKILL.md` excerpt: 7 engines + benchmark panel, 79 skills, 29 swarm teams, Shadow Account loop; core MCP tools keyless, swarm needs `OPENAI_API_KEY`.

Actual repo paths verified by read:
- `src/backtest/engines/canonical.py:1-76` — canonical single-name equity engine: `signal.shift(1)`, `turnover * slippage (0.0005)`, Sharpe/CAGR/DD/excess. No options, no Greeks, no legs, no IV.
- `src/backtest/lean_engine.py:110-360` — closest local analogue to `BaseEngine`: `SlippageModel` (bps), fee model, `Order(fill_price, fee, filled)`, `_fill_pending_orders` T+1. Equity-only.
- `src/research/debate_engine.py:1-166` — 3-persona (bull/bear/neutral) sentiment debate, confidence-weighted Q-score, ±0.33 stance bands, fail-soft per-agent try/except. No rounds, no risk debate, no typed intent.
- `src/research/alptrading_debate.py:1-185` — deterministic AlpacaTradingAgent port: 5 `AnalystReport`s → `run_investment_debate` (alternating bull/bear, judge at `2N`, `judge_margin=0.15`) → `run_risk_debate` (risky/safe/neutral rotation, judge at `3N`, any flag downgrades BUY→HOLD) → ATR sizer + `SafetyGuard.check_order` → typed `TradeIntent(paper=True, live=False)`. Stocks-only (no SHORT opens).
- `src/risk/alptrading_safety.py:1-306` — `SafetyGuard`: kill-switch file, notional cap $10k, concentration 20%, daily-loss 5%, DD-from-HWM 10%, rejection-streak halt, NaN-safe `_finite_float`, risk-reducing bypass; plus `IntradayMarginState` 4×/ $2k-floor paper mirror. This is the local Mandate equivalent.
- `src/execution/paper_executor.py:38-80` — idempotent plan executor (`plan.json` → fills/orders logs, kill-switch re-check, position reconcile). Paper Alpaca only.
- `src/research/agents/workflow.py:1-269` — langgraph `ResearchWorkflow`: research → regime → spec → codegen (RestrictedPython + bandit) → reflection (runs `run_backtest`, Sharpe>1 gate, ≤3 retries). LLM-gated (Gemini), offline tests skip without `langgraph`.
- `docs/GS_QUANT_PORT_PLAN.md:45-74` — planned-but-absent: `src/pricing/bs.py` (`bs_price`/`bs_greeks`), `src/risk/scenario.py`, `EqOptionValidator` (`iv_coverage>=0.80`, `DTE>7`, fail-closed). `src/pricing/` does NOT exist (glob empty); `src/gs_compat/calendar.py` exists. VRP/options work must land in this planned slot, not as a parallel pricer.
- `strategies/registry.json:1-60` — equities-only evolved entries (`spy_rsi2`, REAL-4/4 gates). No options family. No change proposed here.
- VRP references: only `docs/data/next_gen_proposals.jsonl:122` + `_deliverables/papers-implement-2026-09-09.md:148` (`paper_skewt_vrp_20260909` parent params). No `vrp_sleeve`, `variance_risk`, `options_flow_sleeve` implementation in `src/` (grep: zero hits). VRP sleeve is greenfield.

## 1. What upstream does (patterns worth stealing)

### 1a. Options-backtest engine (`options_portfolio.py` v2)

1. **Single-vol choke `leg_iv(S,K,base,skew,curvature)`** — every pricing site (open, mark, Greeks, American continuation) goes through one function. Docstring quantifies the bug it kills: 30-day 10%-OTM call at `skew=-0.15` misprices +16.7% of premium (+93% at 20% OTM) if opened on-smile but marked flat. Adopt verbatim as principle.
2. **HV synth with explicit warm-up contract** — `historical_volatility(close, window=30, default_iv=0.3)`: `log_ret.rolling(30).std()*sqrt(252)`, `.fillna(default_iv)`; warm-up bars prime signals but never enter fills/equity/metrics (`evaluation_start_index`, same convention as equity `BaseEngine`). Matches repo T+1 discipline.
3. **Next-bar-close fills, dated explicitly** — signal dated T fills at T+1 close EOD (`same_day_fill=False` default; opt-in flag only). Post-2026-09-01 invariant. Mirrors `canonical.py:58` (`signal.shift(1)`) and `run_historic_backtest` Open[t+1].
4. **Multi-leg instructions + partial closes** — signal = `{action: open|close, underlying, legs: [{type, strike, expiry, qty}]}`; `close` with explicit `qty` closes that many contracts (clamped), without `qty` closes whole lot; remainder re-inserted as new immutable `OptionPosition`. `_find_matching_position` tolerance `1e-6` on strike + exact expiry match.
5. **Type folding at the boundary** — `normalise_option_type` (call/calls/c/看涨/认购 → call; typo → raise, never default-to-put). Prevents the "priced as call, settled as put" 10×ITM-at-zero class.
6. **CBOE-style short margin + buying-power reject as data** — `short_margin_per_unit = premium + max(margin_rate*spot − OTM, floor_rate*base)` (defaults 20%/10%); `margin_enabled=True` default; unaffordable opens recorded as `side=reject, reason=insufficient buying power, pnl=0` and counted in `options_rejected_opens`, excluded from `trade_count`. Research opt-out (`margin_enabled=False`) is explicit config, not silent leverage.
7. **Expiry-after-fills ordering** — fills dated the bar-before-expiry settle on the expiry bar; option never carried past expiry, never settled a bar late. American early-exercise heuristic: `intrinsic > continuation*1.02` (continuation priced at same `leg_iv`).
8. **Portfolio Greeks + margin in artifacts** — per-bar `greeks.csv` (delta/gamma/theta/vega/rho summed over `qty*multiplier`), `equity.csv` with `margin_hold`, `metrics.csv` with NaN-safe guards (each metric `None` + `warnings[]` instead of crash on zero-vol/negative-equity/short-path).
9. **Degenerate pricer contract (`quantlib/options.py`)** — `T<=0 or S<=0 or K<=0 → intrinsic`; `sigma<=0 with T>0 → discounted forward intrinsic`; Greeks at expiry carry unit delta (ATM midpoint 0.5 preserves `call−put=1`); IV solver returns `nan` when quote carries no vol info (vega-resolution test), raises outside no-arbitrage bounds. One implementation shared by engine + payoff skill (they merged two drifted copies — cautionary tale for this repo: do NOT create a second BS).

### 1b. Swarm orchestration (`swarm/` + presets)

1. **YAML preset = team + DAG** — `SwarmAgentSpec` (role/tools/skills) + `SwarmTask` (prompt template + `depends_on`). `validate_dag` before run (no cycles, valid refs).
2. **Runtime = topological layers + ThreadPoolExecutor** — parallel where independent, sequential where dependent; background thread + `SwarmStore`/`TaskStore` atomic state + append-only events + stale-run reaper.
3. **Worker = lightweight ReAct via `ChatLLM.chat`** (not full `AgentLoop`) — cost control; token tracking from provider `usage_metadata`, char-heuristic fallback.
4. **Grounding = pre-fetch OHLCV for symbols in `user_vars`** (`fetch_grounding_data`) and inject into prompts — anti-stale-price guard for LLM workers.
5. **DAG gating = fail-closed** — upstream failure → downstream `blocked`, never run portfolio/risk on empty reports.
6. **Output contract = `report.md` wins** — `_resolve_summary` prefers the artifact file over chat tail; keyword router (`swarm_tool.py`) auto-selects preset ("drawdown" → `risk_committee`).
7. **Preset families relevant here** — `investment_committee` / `risk_committee` (bull/bear advocates), `quant_strategy_desk` / `factor_research_committee` (alpha + validation), `crypto_trading_desk` (funding basis — VRP-adjacent thinking).

### 1c. Live-trading guard (for the REJECT section)

Mandate (frozen dataclass: `HardCaps` + `UniverseConstraint` + `ConsentMeta`) → `LiveOrderGuardTool` 6-step fail-closed check (load mandate → expiry → kill-switch → intent → positions/balance → limits) → `commit_mandate` isolated from agent tool registry (no self-auth) → `HALT` sentinel + `flatten_on_halt` + `max_trades_per_day` + `audit.jsonl` (redacted). Tool classification ladder: unmarked = WRITE = guarded (default-deny).

## 2. Gap analysis vs this repo

| Upstream capability | Local status | Verdict |
|---|---|---|
| BS pricer + 5 Greeks, degenerate-safe | `src/pricing/` absent; GS plan §3 unbuilt | GAP — Diff 0 fills the planned slot, quantlib-convention-compatible |
| HV synth + quadratic smile `leg_iv` | No IV anywhere; `volatility_forecast.py` is realized-vol only | GAP — Diff 1, VRP sleeve needs HV−IV spread, not raw HV |
| Multi-leg open/close/partial, next-close fills | `canonical.py` single-position equity; `lean_engine.py` single-leg orders | GAP — Diff 2, paper-only, naked-short banned by default |
| Short margin + reject-as-data | `alptrading_safety.py` notional/concentration caps; no premium-margin concept | GAP — Diff 2 ports `short_margin_per_unit` shrunk to sleeve cap |
| Portfolio Greeks log | None | GAP — Diff 2 `vrp_greeks.csv`, needed for VRP delta-neutrality audit |
| Warm-up/`evaluation_start_index` | Equity engines ad-hoc; `validation.py:156` still calendar-day 90 (GS plan fix pending) | PARTIAL — Diff 2 reuses `business_day_offset` where available, documents dependency |
| Deterministic debate → typed intent + guard | `alptrading_debate.py` already has this shape (debate→risk→sizer→guard→`TradeIntent`) | NO GAP on shape — Diff 3 is a thin DAG-preset wrapper, not a new debate |
| LLM reasoning workers + grounding | `workflow.py` (Gemini, langgraph-gated) + `debate_engine.py` (sentiment sim) | GAP on orchestration only — Diff 3 adds deterministic preset runner; NO new LLM path |
| Mandate/consent/live runner/brokers | `paper_executor.py` + `KillSwitch` + `SafetyGuard`; no mandate doc, no live loop | INTENTIONAL GAP — §5 rejects live adopt outright |

Agent-orchestration detail (`debate_engine.py` vs `alptrading_debate.py` vs swarm):
- `debate_engine.py` is single-shot sentiment averaging (3 personas, one pass, no rounds, no risk stage, dict output). Closest swarm analogue: a single worker with 3 sub-prompts — no DAG value.
- `alptrading_debate.py` already IS the swarm-committee shape in deterministic form: parallel analysts (5 inputs) → bull/bear rounds (`2N`) → trader → risk rotation (`3N`) → manager/guard → typed intent. Its rotation, judge-count, downgrade, and fail-closed tie rules are the parts worth keeping.
- What swarm adds that local lacks: (i) declarative preset (YAML/JSON, inspectable without reading code), (ii) topological scheduler with parallel fan-out + `blocked` propagation, (iii) grounding injection, (iv) `report.md` artifact contract, (v) keyword routing. None of these require an LLM. Diff 3 ports exactly these five as a ~120-line deterministic runner over the existing debate functions.

## 3. Design rules (all additions follow repo idiom)

1. Paper-only, sleeve-scoped: VRP code never touches order paths (`paper_executor.py`, `alpaca_broker.py`, `live_*` untouched); sleeve emits `TradeIntent`-shaped dicts with `paper=True, live=False` for the sandbox/backtest consumer only.
2. No second pricer: one `src/pricing/bs.py` (the GS-plan slot); surface/sleeve import from it. Put-call parity + delta-bounds tests gate drift (same tests the GS plan already specifies).
3. Past-only: HV uses `.shift(1)`-safe rolling (no fill-forward of computed window into its own window — upstream #1293 lesson); signals dated T fill T+1; IV for fill bar is the fill bar's HV (known at fill), never the signal bar's forward info.
4. Fail-closed options risks: naked shorts banned by default (`allow_naked_short=False`); DTE>7 block; `iv_coverage>=0.80` gate (GS-plan values); margin-capped; `same_day_fill` defaults False with explicit opt-in flag.
5. No renames/removals: `canonical.py`, `lean_engine.py`, debate files, safety file untouched; new files only + new tests. Registry/strategies untouched (edge gate still required before any family entry).

## 4. Exact diffs proposed

### Diff 0 — NEW `src/pricing/bs.py` (fills GS-plan §3 slot, quantlib-compatible)

```diff
--- /dev/null
+++ b/src/pricing/bs.py
@@ -0,0 +1,88 @@
+"""Black-Scholes-Merton pricer + Greeks (single implementation).
+
+Slot reserved by docs/GS_QUANT_PORT_PLAN.md §3 (gs-quant has no open BS;
+conventions mirror HKUDS/Vibe-Trading agent/src/quantlib/options.py so a
+future diff against it stays mechanical).
+Conventions: T in years, r/q cont-comp annual; theta per calendar day;
+vega/rho per 1pp; delta/gamma per 1.0 spot. Nothing rounded.
+"""
+from __future__ import annotations
+import math
+from typing import Dict
+try:
+    from scipy.stats import norm
+    _HAS_SCIPY = True
+except ImportError:
+    _HAS_SCIPY = False
+    from statistics import NormalDist as _ND
+    _N = _ND()
+
+def _cdf(x: float) -> float:
+    return float(norm.cdf(x)) if _HAS_SCIPY else _N.cdf(x)
+def _pdf(x: float) -> float:
+    return float(norm.pdf(x)) if _HAS_SCIPY else _N.pdf(x)
+
+def normalise_option_type(t: str) -> str:
+    s = str(t).strip().lower()
+    if s in ("call", "calls", "c"): return "call"
+    if s in ("put", "puts", "p"): return "put"
+    raise ValueError(f"unrecognised option_type {t!r} (call|put only; no defaulting)")
+
+def _intrinsic(S,K,typ): return float(max(S-K,0.0) if typ=="call" else max(K-S,0.0))
+
+def bs_price(S,K,T,r,sigma,option_type="call",q=0.0) -> float:
+    typ = normalise_option_type(option_type)
+    if T<=0 or S<=0 or K<=0: return _intrinsic(S,K,typ)
+    if sigma<=0:
+        dfS,dfK = S*math.exp(-q*T), K*math.exp(-r*T)
+        return float(max(dfS-dfK,0.0) if typ=="call" else max(dfK-dfS,0.0))
+    sT=math.sqrt(T); d1=(math.log(S/K)+(r-q+0.5*sigma**2)*T)/(sigma*sT); d2=d1-sigma*sT
+    dfS,dfK = S*math.exp(-q*T), K*math.exp(-r*T)
+    if typ=="call": return float(dfS*_cdf(d1)-dfK*_cdf(d2))
+    return float(dfK*_cdf(-d2)-dfS*_cdf(-d1))
+
+def bs_greeks(S,K,T,r,sigma,option_type="call",q=0.0) -> Dict[str,float]:
+    typ = normalise_option_type(option_type)
+    if T<=0 or S<=0 or K<=0:
+        if S==K: d=0.5 if typ=="call" else -0.5
+        elif typ=="call": d=1.0 if S>K else 0.0
+        else: d=-1.0 if S<K else 0.0
+        return {"delta":d,"gamma":0.0,"theta":0.0,"vega":0.0,"rho":0.0}
+    sT=math.sqrt(T); d1=(math.log(S/K)+(r-q+0.5*sigma**2)*T)/(sigma*sT); d2=d1-sigma*sT
+    pdf=float(_pdf(d1)); dfS,dfK=math.exp(-q*T),math.exp(-r*T)
+    carry=-(S*dfS*pdf*sigma)/(2*sT)
+    if typ=="call":
+        return {"delta":float(dfS*_cdf(d1)),
+                "gamma":float(dfS*pdf/(S*sigma*sT)),
+                "theta":float((carry-r*K*dfK*_cdf(d2)+q*S*dfS*_cdf(d1))/365.0),
+                "vega":float(S*dfS*pdf*sT/100.0),
+                "rho":float(K*T*dfK*_cdf(d2)/100.0)}
+    return {"delta":float(dfS*(_cdf(d1)-1.0)),
+            "gamma":float(dfS*pdf/(S*sigma*sT)),
+            "theta":float((carry+r*K*dfK*_cdf(-d2)-q*S*dfS*_cdf(-d1))/365.0),
+            "vega":float(S*dfS*pdf*sT/100.0),
+            "rho":float(-K*T*dfK*_cdf(-d2)/100.0)}
```

Rationale: unblocks everything below; scipy-optional (fallback `statistics.NormalDist`) keeps zero-cost Actions green; degenerate branches copy upstream so markers (`test_bs_greeks` parity/delta tests from GS plan) transfer.

### Diff 1 — NEW `src/backtest/options_surface.py` (HV + smile, the `leg_iv` choke)

```diff
--- /dev/null
+++ b/src/backtest/options_surface.py
@@ -0,0 +1,64 @@
+"""Vol surface for the VRP sleeve (paper-only, past-only).
+Pattern: HKUDS/Vibe-Trading agent/backtest/engines/options_portfolio.py v2
+(historical_volatility + iv_smile_adjustment + leg_iv choke).
+"""
+from __future__ import annotations
+import numpy as np, pandas as pd
+
+def historical_volatility(close: pd.Series, window: int = 30,
+                          default_iv: float = 0.30) -> pd.Series:
+    """Annualised HV; leading warm-up + gaps -> default_iv (never backfilled)."""
+    lr = np.log(close / close.shift(1))
+    return (lr.rolling(window).std()*np.sqrt(252)).fillna(default_iv)
+
+def iv_smile_adjustment(S: float, K: float, base_iv: float,
+                        skew: float = -0.15, curvature: float = 0.05) -> float:
+    if S<=0 or K<=0: return max(base_iv, 0.01)
+    m = float(np.log(K/S))
+    return max(float(base_iv + skew*m + curvature*m*m), 0.01)
+
+def leg_iv(S: float, K: float, base_iv: float, skew: float = 0.0,
+           curvature: float = 0.0) -> float:
+    """SOLE vol choke: every pricing/marking/Greek site calls this."""
+    if skew==0 and curvature==0: return float(base_iv)
+    return iv_smile_adjustment(S,K,base_iv,skew,curvature)
+
+def vrp_spread(hv: pd.Series, iv: pd.Series) -> pd.Series:
+    """Variance-risk-premium proxy: HV − IV (positive = premium harvested)."""
+    return hv.subtract(iv).replace([np.inf,-np.inf], np.nan)
```

Rationale: `skew/curvature=0` default = flat surface until a pre-registered smile is justified (each nonzero smile param is a trial-ledger trial); `vrp_spread` is the sleeve's signal primitive.

### Diff 2 — NEW `src/backtest/options_sleeve.py` (VRP paper-only sleeve)

New file (~140 lines; core contract shown):

```python
"""VRP sleeve backtester (paper-only, equities single-underlying, e.g. SPY).
Adapts run_options_backtest day-loop to repo idiom (canonical T+1, SafetyGuard).
FAIL-CLOSED: naked shorts banned unless allow_naked_short=True; DTE>7;
iv_coverage>=0.80; margin-capped; same_day_fill=False default.
"""
from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
from src.pricing.bs import bs_price, bs_greeks
from src.backtest.options_surface import historical_volatility, leg_iv

@dataclass
class VRPSleeveConfig:
    r: float = 0.05; multiplier: float = 1.0; commission: float = 0.001
    margin_rate: float = 0.20; margin_floor: float = 0.10
    min_dte_days: int = 7; min_iv_coverage: float = 0.80
    allow_naked_short: bool = False; same_day_fill: bool = False
    default_iv: float = 0.30; skew: float = 0.0; curvature: float = 0.0

def short_margin_per_unit(opt_type, spot, strike, premium, cfg): ...
def run_vrp_sleeve(close: pd.Series, signals: pd.DataFrame, cfg=VRPSleeveConfig()):
    """close: daily closes; signals: rows {date, action(open|close),
    opt_type, strike, expiry, qty}. Signals dated T fill T+1 close.
    Returns (equity_df, trades_df, greeks_df, metrics_dict)."""
```

Behaviors ported one-to-one (and pinned by tests): next-close fills with `same_day_fill` opt-out; expiry-after-fills; partial-close `qty` clamp + lot-remainder reinsert; `side=reject` rows for buying-power/DTE/coverage/naked-short blocks (excluded from `trade_count`, counted as `vrp_rejected_opens`); per-bar portfolio Greeks + `margin_hold`; metrics with `warnings[]` instead of exceptions. Signal generation itself (HV−IV threshold → short-OTM-put-spread / long-gamma hedge) lives in the hunt brief, NOT in this engine — engine executes dated instructions only (mirrors upstream signal/engine split + `hunt_runner` discipline).

### Diff 3 — NEW `src/research/vibe_preset.py` (deterministic swarm-preset runner, no LLM)

```diff
--- /dev/null
+++ b/src/research/vibe_preset.py
@@ -0,0 +1,70 @@
+"""Deterministic DAG-preset runner over existing debate functions.
+Ports HKUDS/Vibe-Trading swarm contracts (presets, topological_layers,
+grounding, DAG-gating blocked, report.md) WITHOUT any LLM worker.
+Workers are callables over src/research/alptrading_debate.py + debate_engine.py.
+"""
+from __future__ import annotations
+from dataclasses import dataclass, field
+from typing import Callable, Dict, List
+
+@dataclass
+class PresetTask:
+    name: str; run: Callable[[dict], dict]; depends_on: List[str] = field(default_factory=list)
+@dataclass
+class PresetResult:
+    name: str; status: str  # ok | blocked | failed
+    output: dict = field(default_factory=dict)
+
+def validate_dag(tasks: List[PresetTask]) -> None:
+    names = {t.name for t in tasks}
+    if len(names) != len(tasks): raise ValueError("duplicate task name")
+    for t in tasks:
+        for d in t.depends_on:
+            if d not in names: raise ValueError(f"{t.name} depends on unknown {d}")
+    # cycle check (Kahn)
+    import collections
+    indeg = {t.name: len(t.depends_on) for t in tasks}
+    kids = collections.defaultdict(list)
+    for t in tasks:
+        for d in t.depends_on: kids[d].append(t.name)
+    q = [n for n,d in indeg.items() if d==0]
+    seen = 0
+    while q:
+        n = q.pop(); seen += 1
+        for k in kids[n]:
+            indeg[k]-=1
+            if indeg[k]==0: q.append(k)
+    if seen != len(tasks): raise ValueError("cycle in preset DAG")
+
+def run_preset(tasks: List[PresetTask], ctx: dict) -> Dict[str, PresetResult]:
+    """Topological layers; upstream fail/block -> downstream blocked (fail-closed)."""
+    validate_dag(tasks); out: Dict[str,PresetResult] = {}; done=set()
+    pending = list(tasks)
+    while pending:
+        layer = [t for t in pending if all(d in done for d in t.depends_on)]
+        if not layer:  # unsatisfiable -> block remainder
+            for t in pending: out[t.name]=PresetResult(t.name,"blocked",{"reason":"unsatisfied deps"})
+            break
+        for t in layer:
+            if any(out[d].status!="ok" for d in t.depends_on):
+                out[t.name]=PresetResult(t.name,"blocked",{"upstream":[d for d in t.depends_on if out[d].status!="ok"]})
+            else:
+                try: out[t.name]=PresetResult(t.name,"ok",t.run(ctx))
+                except Exception as e: out[t.name]=PresetResult(t.name,"failed",{"error":str(e)})
+            done.add(t.name)
+        pending = [t for t in pending if t.name not in out]
+    return out
```

Wiring (no existing-file edit): a `VRP_COMMITTEE` preset list built in the new module maps `analysts → run_investment_debate → run_risk_debate → build_intent(+SafetyGuard)` with a grounding step (attach latest close/HV/IV into `ctx`, mirroring `fetch_grounding_data`) and a `report.md`-shaped `summary()` (markdown string in result, file write left to caller artifact path). Keyword routing (`def pick_preset(question)`) mirrors `swarm_tool.py` minimally (`"vrp"/"vol"/"drawdown"` → committee variant). `workflow.py`, `debate_engine.py`, `alptrading_debate.py` untouched.

### Diff 4 — validator delta in `src/backtest/validators/statistical.py` (additive subclass)

```diff
--- a/src/backtest/validators/statistical.py
+++ b/src/backtest/validators/statistical.py
@@ class StatisticalValidator: ...
+@dataclass
+class VRPValidator(StatisticalValidator):
+    """Fail-closed gates for any VRP/options claim (GS-plan EqOption values)."""
+    min_dte_days: int = 7
+    min_iv_coverage: float = 0.80
+    def check(self, legs, bars) -> tuple[bool, list[str]]:
+        reasons = []
+        if (bars["dte"].min() <= self.min_dte_days): reasons.append("DTE<=7 leg present")
+        if (bars["iv_covered"].mean() < self.min_iv_coverage): reasons.append("iv_coverage<0.80")
+        return (not reasons, reasons)
```

Keeps `p<0.01 IS / p<0.05 WFO / WFE≥0.7` parent thresholds (GS plan §5); DSR trial-count must include smile params (`skew`, `curvature`, HV window) when nonzero.

### Diff 5 — NEW `tests/test_vibetrade_adopt.py` (mirrors `test_lean_port`/`test_alptrading_port` style)

```python
"""Gates: BS parity/delta bounds; leg_iv choke identity; next-close fill;
naked-short default reject; partial-close remainder; DTE/coverage gates;
preset DAG block propagation + cycle refusal."""
# 8 tests, all synthetic/offline, <5s:
# test_bs_put_call_parity / test_bs_delta_bounds / test_leg_iv_flat_identity
# test_vrp_next_close_fill (signal T prices T+1 close, same_day_fill=False)
# test_vrp_naked_short_banned_by_default / test_vrp_partial_close_remainder
# test_vrp_dte_and_coverage_gates / test_preset_blocked_propagation_and_cycle
```

## 5. What to REJECT (explicit, with grounds)

**REJECT 1 — Live autonomous execution (LiveRunner, broker connectors, mandate-driven auto-trading).**
Grounds: (i) repo mandate is zero-cost GitHub Actions + Alpaca *paper* only (`AGENTS.md`, `PAPER_BROKER_SETUP.md`); upstream live path needs user-held broker OAuth + persistent runner + per-connection OS-keyring secrets — no CI equivalent; (ii) upstream's own safety model (mandate/consent/commit isolation) is a second auth system alongside `SafetyGuard`+`KillSwitch` — running both invites guard-confusion; (iii) options live adds assignment/early-exercise/pin-risk ops the paper sleeve never models; (iv) PDT/intraday-margin rules already constrain small equity accounts (see `web-research/strategies.md:354`) — autonomous options flow multiplies that surface. Adopt the *guard ideas* (default-deny tool ladder, HALT sentinel parity, redacted audit) into `SafetyGuard`/audit — never the execution loop.

**REJECT 2 — LLM swarm workers as order-path reasoning (`ChatLLM`, 12-provider fan-out, `run_swarm` spending `OPENAI_API_KEY`).**
Grounds: nondeterministic prompts cannot pass the edge gate (pre-reg → WF → 200-perm → DSR); grounding injection mitigates stale prices but not fabulated Greeks; cost/quota violates zero-cost mandate. LLM stays in `workflow.py` research lane (RestrictedPython+bandit sandbox, human-read specs), never in fill/sizing/guard decisions. Diff 3 is deterministic precisely for this reason.

**REJECT 3 — Full 9-engine + loader-registry + Alpha Zoo import.**
Grounds: per-market microstructure engines (ChinaA T+1/limits, India STT/SEBI/GST stack, crypto funding, forex) + 18-source fallback chains solve markets this repo does not trade; `Alpha Zoo` 452 alphas × trial-ledger deflation would tighten the DSR bar for the entire registry. Cherry-pick (Diffs 0–2) is the proportionate adopt; composite/cross-market calendars stay out.

**REJECT 4 — Shadow Account loop as strategy discovery.**
Grounds: journal-mining (`analyze_trade_journal → extract_shadow_strategy → run_shadow_backtest`) learns from *paper* fills that never experienced assignment, pin risk, or wide short-dated spreads — disposition-effect repair on simulated fills is circular. Keep as behavioral-review tooling only, never as a hunt family.

**REJECT 5 — American-exercise + barrier options + smile-calibrated live pricing in v1.**
Grounds: upstream v2 American heuristic + `barrier_option_price` (Reiner-Rubinstein) are validated research tools, but VRP sleeve v1 is European, DTE>7, flat-surface. Adopt the *degenerate-handling contract* now, the exotics after a pre-registered follow-up with its own edge gate.

## 6. Test plan (targeted-only, per AGENTS.md)

1. `PYTHONPATH=. pytest tests/test_vibetrade_adopt.py -q` — new gate (parity, delta bounds, choke identity, T+1 fill date, naked-short reject, partial remainder, DTE/coverage, DAG block+cycle).
2. `PYTHONPATH=. pytest tests/test_lean_port.py tests/test_alptrading_port.py tests/test_gs_calendar.py -q` — regression: canonical/lean T+1, debate intent shape, calendar untouched.
3. `PYTHONPATH=. pytest tests/test_session4_lookahead.py -q` — T+1 lookahead still holds with sleeve present (sleeve imports only, no engine monkey-patch).
4. Offline VRP smoke (no network): synthetic SPY-like closes → `historical_volatility` → flat-surface `run_vrp_sleeve` on 2-leg spread instructions → eyeball `equity.csv`-shaped frame + `greeks.csv` delta≈neutral + `vrp_rejected_opens==1` on the naked-short probe bar.
5. `ruff check src/pricing/bs.py src/backtest/options_surface.py src/backtest/options_sleeve.py src/research/vibe_preset.py tests/test_vibetrade_adopt.py` — lint (no config file per repo rule).
6. `bandit -r src/pricing/ src/backtest/options_surface.py src/backtest/options_sleeve.py src/research/vibe_preset.py` — expected clean (pure numpy/pandas/math, no network, no eval/exec).
7. Edge-gate path (follow-up hunt, NOT this diff): pre-register VRP hypothesis (`preregister.py freeze`) → `run_full_backtest` + sleeve report → 200-perm + CPCV + walk-forward OOS → DSR ledger → only then propose `strategies/<family>.yaml` + registry entry.

## 7. Risks

- HV-as-IV is a model, not a print: flat-surface backtests overstate short-premium edge where skew is steep (OTM puts). Mitigated by flat-default + DTE>7 + coverage gate + `warnings[]` on low-coverage bars; smile calibration is a separate pre-registered trial, never a silent tweak.
- `scipy` availability: `bs.py` falls back to `statistics.NormalDist` (parity test covers both paths); sleeve never imports `scipy.optimize` (no IV inversion in v1 — HV synth only, sidesteps the `nan`-band identifiability issue by construction).
- Smile-param trial inflation: any nonzero `skew/curvature` or HV-window change counts as a trial in `trial_ledger.py` DSR — documented in Diff 2 docstring so the gate stays honest.
- Preset-runner scope creep: `vibe_preset.py` is deliberately not a task store / thread pool / web server — persistence stays in `docs/data/ops/` + existing audit; background threads stay out (Actions-friendly).
- Upstream drift: pin assessed commit in the hunt brief; re-run parity/choke/fill-date tests on any re-vendor (upstream merged two drifted pricers once — §1a.9).

*Sources: HKUDS/Vibe-Trading `agent/backtest/engines/options_portfolio.py`, `agent/src/quantlib/options.py`, `agent/backtest/engines/base.py`, DeepWiki 4/5/10, `agent/SKILL.md`; local `src/backtest/engines/canonical.py`, `src/backtest/lean_engine.py`, `src/research/debate_engine.py`, `src/research/alptrading_debate.py`, `src/risk/alptrading_safety.py`, `src/execution/paper_executor.py`, `src/research/agents/workflow.py`, `docs/GS_QUANT_PORT_PLAN.md`, `strategies/registry.json` (read-only).*
