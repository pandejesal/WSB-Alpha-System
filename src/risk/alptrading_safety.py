"""AlpacaTradingAgent safety-guard port (Python, deterministic, no LLM).

Source: https://github.com/huygiatrng/AlpacaTradingAgent
  tradingagents/safety/guardrails.py (406 lines)

Ported faithfully: DEFAULT_SAFETY_CONFIG keys, SafetyVerdict, kill-switch
flag file (ops `touch` halts everything, release restores), JSON state file
(high-water mark, rejection streak), NaN-safe number parsing (a NaN that
reaches a comparison silently passes every breaker — parsed as unavailable
instead), pre-trade notional + concentration caps (skipped, not guessed,
when account data is missing), daily-loss and drawdown-from-HWM circuit
breakers, consecutive-rejection halt, risk-reducing exits bypass exposure
and breaker checks (a halt must never trap a position; kill switch still
blocks everything).

Deltas: LLM token budget dropped (no LLM calls in this repo's beats; free
tier guarded by the VPN rotator instead). Thread lock dropped (single
process beats). Alert hook dropped (no network). Defaults tightened for
the user mandate (notional 25k->10k, concentration 25%->20%, daily halt
10%->5%, drawdown halt 15%->10%) — overridable via config dict.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_SAFETY_CONFIG: dict[str, Any] = {
    "safety_enabled": True,
    "max_trade_notional_usd": 10_000.0,  # 0 = uncapped
    "max_symbol_concentration_pct": 20.0,  # of account equity; 0 = uncapped
    "daily_loss_halt_pct": 5.0,
    "max_drawdown_halt_pct": 10.0,
    "max_consecutive_rejections": 5,
}


@dataclass
class SafetyVerdict:
    allowed: bool
    reasons: list[str] = field(default_factory=list)
    checks: dict[str, dict] = field(default_factory=dict)


def _finite_float(value: Any) -> float | None:
    """NaN/inf/garbage -> None (unavailable), never a silent pass."""
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


class SafetyGuard:
    def __init__(self, config: dict[str, Any] | None = None,
                 state_path: Path | None = None,
                 kill_switch_path: Path | None = None):
        merged = dict(DEFAULT_SAFETY_CONFIG)
        if config:
            for key in merged:
                if config.get(key) is not None:
                    merged[key] = config[key]
        self.config = merged
        self.state_path = Path(state_path or Path.home() / ".wsb-alpha" / "safety-state.json")
        self.kill_switch_path = Path(kill_switch_path or Path.home() / ".wsb-alpha" / "KILL_SWITCH")
        self._state = self._load_state()

    def _load_state(self) -> dict[str, Any]:
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                raw.setdefault("high_water_mark", None)
                raw.setdefault("consecutive_rejections", 0)
                return raw
        except (OSError, ValueError):
            pass
        return {"high_water_mark": None, "consecutive_rejections": 0}

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._state, indent=2), encoding="utf-8")
        os.replace(tmp, self.state_path)

    @property
    def enabled(self) -> bool:
        return bool(self.config.get("safety_enabled", True))

    def kill_switch_active(self) -> bool:
        return self.kill_switch_path.exists()

    def kill_switch_reason(self) -> str:
        try:
            return self.kill_switch_path.read_text(encoding="utf-8").strip()
        except OSError:
            return ""

    def engage_kill_switch(self, reason: str = "manual halt") -> None:
        from datetime import datetime, timezone
        self.kill_switch_path.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).isoformat()
        self.kill_switch_path.write_text(f"{reason} (engaged {stamp})", encoding="utf-8")

    def release_kill_switch(self) -> None:
        try:
            self.kill_switch_path.unlink()
        except FileNotFoundError:
            pass

    def record_order_result(self, success: bool) -> None:
        if success:
            self._state["consecutive_rejections"] = 0
        else:
            self._state["consecutive_rejections"] = int(self._state.get("consecutive_rejections", 0)) + 1
        self._save_state()

    def record_equity(self, equity: float) -> None:
        eq = _finite_float(equity)
        if eq is None:
            return
        hwm = _finite_float(self._state.get("high_water_mark"))
        if hwm is None or eq > hwm:
            self._state["high_water_mark"] = eq
            self._save_state()

    def check_order(self, symbol: str, notional: float,
                    account: dict[str, float] | None = None,
                    position_value: float | None = None,
                    risk_reducing: bool = False) -> SafetyVerdict:
        if not self.enabled:
            return SafetyVerdict(True, checks={"safety": {"status": "skipped", "detail": "disabled"}})
        reasons: list[str] = []
        checks: dict[str, dict] = {}

        if self.kill_switch_active():
            return SafetyVerdict(False, [f"kill switch active: {self.kill_switch_reason()}"],
                                 {"kill_switch": {"status": "fail"}})
        checks["kill_switch"] = {"status": "pass"}

        cap = _finite_float(self.config.get("max_trade_notional_usd", 0)) or 0.0
        amt = _finite_float(notional)
        if cap > 0 and amt is not None and amt > cap:
            reasons.append(f"notional {amt:.2f} exceeds cap {cap:.2f}")
            checks["notional"] = {"status": "fail", "notional": amt, "cap": cap}
        else:
            checks["notional"] = {"status": "pass"}

        if risk_reducing:
            checks["mode"] = {"status": "pass", "detail": "risk-reducing exit bypasses exposure/breakers"}
            return SafetyVerdict(not reasons, reasons, checks)

        conc = _finite_float(self.config.get("max_symbol_concentration_pct", 0)) or 0.0
        equity = _finite_float((account or {}).get("equity"))
        pos = _finite_float(position_value)
        if conc > 0 and equity is not None and equity > 0:
            total = (pos or 0.0) + (amt or 0.0)
            if total / equity * 100 > conc:
                reasons.append(f"concentration {total / equity * 100:.1f}% exceeds {conc}% cap")
                checks["concentration"] = {"status": "fail"}
            else:
                checks["concentration"] = {"status": "pass"}
        else:
            checks["concentration"] = {"status": "skipped"}

        last = _finite_float((account or {}).get("last_equity"))
        halt = _finite_float(self.config.get("daily_loss_halt_pct", 0)) or 0.0
        if equity is not None and last is not None and last > 0 and halt > 0:
            drop = (equity - last) / last * 100
            if drop <= -halt:
                reasons.append(f"daily loss {drop:.1f}% hit -{halt}% halt")
                checks["daily_loss"] = {"status": "fail", "drop_pct": round(drop, 2)}
            else:
                checks["daily_loss"] = {"status": "pass"}
        else:
            checks["daily_loss"] = {"status": "skipped"}

        dd_halt = _finite_float(self.config.get("max_drawdown_halt_pct", 0)) or 0.0
        hwm = _finite_float(self._state.get("high_water_mark"))
        if equity is not None:
            if hwm is None or equity > hwm:
                self._state["high_water_mark"] = equity
                self._save_state()
                checks["drawdown"] = {"status": "pass"}
            elif dd_halt > 0 and hwm > 0 and (equity - hwm) / hwm * 100 <= -dd_halt:
                reasons.append(f"drawdown from high-water mark hit -{dd_halt}% halt")
                checks["drawdown"] = {"status": "fail"}
            else:
                checks["drawdown"] = {"status": "pass"}
        else:
            checks["drawdown"] = {"status": "skipped"}

        max_rej = int(self.config.get("max_consecutive_rejections", 0) or 0)
        streak = int(self._state.get("consecutive_rejections", 0))
        if max_rej > 0 and streak >= max_rej:
            reasons.append(f"{streak} consecutive rejections (data/connectivity glitch?)")
            checks["rejections"] = {"status": "fail", "streak": streak}
        else:
            checks["rejections"] = {"status": "pass", "streak": streak}

        _ = symbol
        return SafetyVerdict(not reasons, reasons, checks)


# ---------------------------------------------------------------------------
# Intraday margin mirror (Alpaca Intraday Margin Rule, paper-only model).
#
# Mechanics mirrored from the Alpaca docs:
#  - Intraday Buying Power replaces Day Trade Buying Power: a RUNNING
#    calculation through the day from equity + positions + intraday P&L.
#  - 4x intraday leverage for accounts with equity >= $2,000 (was $25,000
#    under PDT); below that, cash-only (1x, no margin debit).
#  - Pre-Trade Checks reject orders that would put the account into margin
#    deficit (fail-closed, real time).
#  - Intraday Margin Calls replace Day Trade Margin Calls: a deficit that
#    stays unmet for 5 business days restricts the account (no new
#    debit balances / shorts) for up to 90 days. Risk-reducing exits
#    always bypass, so a restriction can never trap a position.
#  - De minimis: deficits under min($1,000, 5% of equity) raise no call.
# ---------------------------------------------------------------------------

MARGIN_EQUITY_FLOOR = 2000.0
INTRADAY_LEVERAGE = 4.0
MARGIN_CALL_DAYS = 5


@dataclass
class IntradayMarginState:
    start_day_equity: float = 100000.0
    cash: float = 100000.0
    gross_exposure: float = 0.0
    intraday_pnl: float = 0.0  # realized + unrealized, may be negative
    open_calls: list[dict[str, Any]] = field(default_factory=list)
    restricted_until: str = ""  # ISO date; empty = unrestricted


def intraday_buying_power(state: IntradayMarginState) -> float:
    """Running intraday margin available for NEW positions."""
    base = _finite_float(state.start_day_equity) or 0.0
    pnl = _finite_float(state.intraday_pnl) or 0.0
    exposure = max(0.0, _finite_float(state.gross_exposure) or 0.0)
    equity_now = base + pnl
    lev = INTRADAY_LEVERAGE if equity_now >= MARGIN_EQUITY_FLOOR else 1.0
    return max(0.0, equity_now * lev - exposure)


def _de_minimis(deficit: float, equity: float) -> bool:
    if deficit <= 0:
        return True
    return deficit < min(1000.0, 0.05 * max(equity, 0.0))


def check_intraday_order(state: IntradayMarginState, notional: float,
                         risk_reducing: bool = False,
                         today: str = "") -> SafetyVerdict:
    """Pre-Trade Check: reject orders that would create a margin deficit."""
    if state.restricted_until and (not today or today <= state.restricted_until):
        if not risk_reducing:
            return SafetyVerdict(False, ["account restricted (unmet margin call): "
                                         "no new debit balances until "
                                         f"{state.restricted_until}"],
                                 {"restriction": {"status": "fail"}})
    ibp = intraday_buying_power(state)
    amt = _finite_float(notional) or 0.0
    if risk_reducing:
        return SafetyVerdict(True, [],
                             {"intraday_bp": {"status": "pass", "available": round(ibp, 2),
                                              "detail": "risk-reducing bypass"}})
    if amt > ibp:
        deficit = amt - ibp
        equity_now = (state.start_day_equity or 0.0) + (state.intraday_pnl or 0.0)
        if _de_minimis(deficit, equity_now):
            return SafetyVerdict(True, [],
                                 {"intraday_bp": {"status": "pass",
                                                  "detail": "de minimis deficit"}})
        return SafetyVerdict(False, [f"order ${amt:,.0f} exceeds intraday buying "
                                     f"power ${ibp:,.0f} (deficit ${deficit:,.0f})"],
                             {"intraday_bp": {"status": "fail",
                                              "available": round(ibp, 2),
                                              "deficit": round(deficit, 2)}})
    return SafetyVerdict(True, [],
                         {"intraday_bp": {"status": "pass",
                                          "available": round(ibp, 2)}})


def record_margin_call(state: IntradayMarginState, deficit: float,
                       today: str) -> dict[str, Any]:
    """Log an intraday margin call; escalate to restriction after 5 days unmet."""
    call = {"date": today, "deficit": deficit, "met": False}
    state.open_calls.append(call)
    unmet = [c for c in state.open_calls if not c.get("met")]
    if len(unmet) >= MARGIN_CALL_DAYS:
        state.restricted_until = today  # caller extends to +90d in production
        call["escalated"] = True
    return call


def meet_margin_calls(state: IntradayMarginState) -> int:
    """Mark all open calls met (deposit / liquidation covered the deficit)."""
    n = sum(1 for c in state.open_calls if not c.get("met"))
    for c in state.open_calls:
        c["met"] = True
    state.restricted_until = ""
    return n
