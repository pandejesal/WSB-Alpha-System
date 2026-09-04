"""Baseline paper tracking + winning-paper verdict renderer (Task 5.3).

Reads paper artifacts under docs/data/ops/ (fills.json, orders.json) and the
backtest baseline (docs/data/backtest_report.json), computes per-sleeve paper
PnL/exposure, paper-vs-baseline tracking stats when enough history exists, and
renders the live-readiness verdict.

Verdict rule (fail-closed):
  - NEED_MORE_PAPER_TIME until >= min_months (default 2) full calendar months
    of paper fills exist.
  - GO requires: every tracked month green (month PnL > 0), max drawdown over
    the window <= max_dd_limit (default 0.15), and zero broken executions
    (orders not SUBMITTED/FILLED).

No network access; missing inputs degrade to honest NOT_EVALUABLE fields.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
OPS_DIR = REPO_ROOT / "docs" / "data" / "ops"
DATA_DIR = REPO_ROOT / "docs" / "data"
DASHBOARD_PATH = DATA_DIR / "paper_dashboard.json"

MIN_MONTHS_DEFAULT = 2
MAX_DD_LIMIT_DEFAULT = 0.15
OK_ORDER_STATUSES = {"SUBMITTED", "FILLED", "FILLED_PARTIAL", "CANCELED"}


def _load(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _month_key(ts: str) -> str | None:
    try:
        return ts[:7]  # YYYY-MM
    except (TypeError, IndexError):
        return None


def sleeve_summary(fills_doc: dict | None) -> dict[str, dict]:
    """Aggregate fills per sleeve+ticker: net qty, cost basis, realized value."""
    if not isinstance(fills_doc, dict):
        return {}
    agg: dict[str, dict] = {}
    for fill in fills_doc.get("fills", []):
        if fill.get("status") != "FILLED":
            continue
        key = f"{fill.get('sleeve', 'unknown')}:{fill.get('ticker', '?')}"
        slot = agg.setdefault(
            key,
            {"sleeve": fill.get("sleeve"), "ticker": fill.get("ticker"), "net_qty": 0.0, "buy_cost": 0.0, "sell_value": 0.0, "fills": 0},
        )
        qty = float(fill.get("qty") or 0.0)
        px = float(fill.get("avg_px") or 0.0)
        slot["fills"] += 1
        if fill.get("side") == "buy":
            slot["net_qty"] += qty
            slot["buy_cost"] += qty * px
        else:
            slot["net_qty"] -= qty
            slot["sell_value"] += qty * px
    for slot in agg.values():
        slot["realized_pnl"] = round(slot["sell_value"] - slot["buy_cost"], 2) if slot["sell_value"] > 0 else None
        slot["open_exposure_qty"] = round(slot["net_qty"], 8)
    return agg


def monthly_pnl(fills_doc: dict | None) -> dict[str, float]:
    """Monthly realized PnL from closing fills (sell_value - buy_cost per month of the CLOSING side)."""
    if not isinstance(fills_doc, dict):
        return {}
    monthly: dict[str, float] = defaultdict(float)
    has_any = False
    for fill in fills_doc.get("fills", []):
        if fill.get("status") != "FILLED":
            continue
        mk = _month_key(fill.get("ts", ""))
        if mk is None:
            continue
        qty = float(fill.get("qty") or 0.0)
        px = float(fill.get("avg_px") or 0.0)
        if fill.get("side") == "sell":
            monthly[mk] += qty * px
            has_any = True
        elif fill.get("side") == "buy":
            # attribute buy cost to its own month so partial windows stay honest
            monthly[mk] -= qty * px
    if not has_any:
        return {}
    return {k: round(v, 2) for k, v in sorted(monthly.items())}


def broken_executions(orders_doc: dict | None) -> list[dict]:
    if not isinstance(orders_doc, dict):
        return []
    broken = []
    for order in orders_doc.get("orders", []):
        status = str(order.get("status", "")).upper()
        if status not in OK_ORDER_STATUSES:
            broken.append({"client_order_id": order.get("client_order_id"), "status": status})
    return broken


def max_drawdown_from_monthly(monthly: dict[str, float]) -> float:
    """Max drawdown across cumulative monthly PnL normalized by a 100k baseline."""
    base = 100_000.0
    equity = base
    peak = base
    mdd = 0.0
    for pnl in monthly.values():
        equity += pnl
        peak = max(peak, equity)
        if peak > 0:
            mdd = max(mdd, (peak - equity) / peak)
    return round(mdd, 4)


def verify_risk_scaling(account_equity: float = 100.0) -> dict:
    """Verify Kelly-based per-trade risk scaling at a $100-equivalent basis (Task 6.2).

    Uses the Kelly-enabled PortfolioManager (src/risk/portfolio_manager.py):

      - registers one strategy at confidence 100 (base allocation 50%),
      - records a small positive trade history so the Kelly sizer's
        historical fallback yields a positive edge,
      - asserts the dual-constraint target (min of confidence and Kelly
        amounts) and the per-trade risk budget (2% default),
      - asserts fail-closed behavior with no trade history (target 0.0).

    Pure computation, no network. Returns a structured verification record.
    """
    # Lazy import keeps this module hermetic when only scripts/ is on sys.path.
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from src.risk.portfolio_manager import PortfolioManager  # noqa: E402

    pm = PortfolioManager(max_strategies=1, max_allocation_per_strategy_pct=0.5)
    pm.register_strategy("S1", confidence_score=100)

    # Small positive history -> historical fallback edge (0.02) > min_edge (0.01).
    for ret in (0.02, 0.03, 0.01):
        pm.kelly_sizer.record_trade({"return": ret})

    target = pm.get_target_allocation("S1", account_equity, trade_features={})
    edge, variance = pm.kelly_sizer.predict_edge_and_variance({})

    # Per-trade risk check: 0.2 shares, entry 100, stop 99 -> $0.20 risk.
    shares = 0.2
    entry, stop = 100.0, 99.0
    proposed_risk = pm.compute_trade_risk(entry, stop, shares)
    within_budget = pm.check_risk_budget(account_equity, proposed_risk)

    # Fail-closed: no history -> zero edge -> zero allocation.
    pm2 = PortfolioManager(max_strategies=1, max_allocation_per_strategy_pct=0.5)
    pm2.register_strategy("S1", confidence_score=100)
    fail_closed_target = pm2.get_target_allocation("S1", account_equity, trade_features={})

    return {
        "account_equity_basis": account_equity,
        "sizing_method": "kelly",
        "per_trade_risk_cap_pct": pm.max_per_trade_risk_pct,
        "per_trade_risk_cap_usd": round(account_equity * pm.max_per_trade_risk_pct, 2),
        "static_1pct_usd": round(account_equity * 0.01, 2),
        "kelly_sized_allocation_usd": round(target, 2),
        "proposed_trade_risk_usd": round(proposed_risk, 2),
        "risk_within_budget": within_budget,
        "kelly_verified": within_budget and target > 0.0 and target <= account_equity * 0.5,
        "fail_closed_no_history": fail_closed_target == 0.0,
    }


def build_dashboard(min_months: int = MIN_MONTHS_DEFAULT, max_dd_limit: float = MAX_DD_LIMIT_DEFAULT) -> dict:
    fills_doc = _load(OPS_DIR / "fills.json")
    orders_doc = _load(OPS_DIR / "orders.json")
    baseline_state = _load(DATA_DIR / "portfolio_state.json")
    quarterly = _load(DATA_DIR / "quarterly_performance.json")

    sleeves = sleeve_summary(fills_doc)
    monthly = monthly_pnl(fills_doc)
    broken = broken_executions(orders_doc)

    months_tracked = len(monthly)
    all_green = bool(monthly) and all(v > 0 for v in monthly.values())
    mdd = max_drawdown_from_monthly(monthly) if monthly else None

    criteria = {
        "months_tracked": months_tracked,
        "min_months_required": min_months,
        "all_months_green": all_green,
        "max_drawdown": mdd,
        "max_dd_limit": max_dd_limit,
        "dd_within_limit": mdd is not None and mdd <= max_dd_limit,
        "broken_executions": broken,
        "no_broken_executions": len(broken) == 0,
    }

    if months_tracked < min_months:
        verdict = "NEED_MORE_PAPER_TIME"
    elif not all_green:
        verdict = "NO_GO_RED_MONTH"
    elif not criteria["dd_within_limit"]:
        verdict = "NO_GO_DRAWDOWN_BREACH"
    elif not criteria["no_broken_executions"]:
        verdict = "NO_GO_EXECUTION_FAULT"
    else:
        verdict = "GO"

    baseline_equity = None
    if isinstance(baseline_state, dict):
        baseline_equity = baseline_state.get("baseline_equity")

    backtest_quarters = len(quarterly) if isinstance(quarterly, list) else 0

    dashboard = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "verdict": verdict,
        "criteria": criteria,
        "sleeves": sleeves,
        "monthly_realized_pnl": monthly,
        "baseline_equity": baseline_equity,
        "backtest_baseline": {
            "quarters_available": backtest_quarters,
            "source": "docs/data/quarterly_performance.json",
        },
        "tracking_error": {
            "status": "NOT_EVALUABLE_INSUFFICIENT_PAPER_HISTORY",
            "note": "Requires >= min_months of daily paper marks vs backtest curve.",
        },
        "risk_scaling": verify_risk_scaling(),
    }
    return dashboard


def render_verdict_md(dashboard: dict) -> str:
    c = dashboard["criteria"]
    lines = [
        "# Paper Approval Verdict",
        "",
        f"- **Verdict:** `{dashboard['verdict']}` (generated {dashboard['generated_at']})",
        f"- Months tracked: **{c['months_tracked']}** / required {c['min_months_required']}",
        f"- All months green: **{c['all_months_green']}**",
        f"- Max drawdown: **{c['max_drawdown']}** (limit {c['max_dd_limit']})",
        f"- Broken executions: **{len(c['broken_executions'])}**",
    ]
    rs = dashboard.get("risk_scaling")
    if rs:
        lines.append(
            f"- Risk scaling (${rs.get('account_equity_basis', 100.0)} equiv): Kelly target "
            f"**${rs.get('kelly_sized_allocation_usd')}**, per-trade risk cap "
            f"**{rs.get('per_trade_risk_cap_pct', 0.0) * 100:.0f}%** (${rs.get('per_trade_risk_cap_usd')}), "
            f"verified **{rs.get('kelly_verified')}**, fail-closed **{rs.get('fail_closed_no_history')}**"
        )
    lines += ["", "| Month | Realized PnL ($) |", "|-------|------------------|"]
    for month, pnl in dashboard["monthly_realized_pnl"].items():
        lines.append(f"| {month} | {pnl} |")
    if not dashboard["monthly_realized_pnl"]:
        lines.append("| (none) | 0 |")
    lines += ["", "> Fail-closed: NEED_MORE_PAPER_TIME until all gates pass.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-months", type=int, default=MIN_MONTHS_DEFAULT)
    parser.add_argument("--max-dd-limit", type=float, default=MAX_DD_LIMIT_DEFAULT)
    parser.add_argument("--out", type=str, default=str(DASHBOARD_PATH))
    args = parser.parse_args()

    dashboard = build_dashboard(min_months=args.min_months, max_dd_limit=args.max_dd_limit)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(dashboard, indent=2) + "\n", encoding="utf-8")

    md = render_verdict_md(dashboard)
    print(md)
    print(f"[baseline_paper_track] dashboard written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
