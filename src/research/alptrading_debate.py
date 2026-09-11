"""AlpacaTradingAgent debate-pipeline port (deterministic, no LLM, no network).

Source: https://github.com/huygiatrng/AlpacaTradingAgent
  graph/conditional_logic.py + setup.py, agents/schemas.py,
  agents/managers/*, agents/risk_mgmt/*, graph/signal_processing.py

Upstream pipeline: 5 parallel analysts -> bull/bear debate (N rounds,
alternating, judge on count >= 2N) -> trader proposal -> risky/safe/
neutral risk debate (rotation, judge on count >= 3N) -> risk manager ->
typed TradeIntent (BUY/HOLD/SELL or LONG/NEUTRAL/SHORT).

This port keeps the pipeline SHAPE and all deterministic parts:
round counting, speaker rotation, structured intent, protective-price
extraction (absolute prices only — relative/qualitative guidance yields
None, never a guessed order level), signal-pattern parsing. The LLM
rhetoric inside each node is replaced by score arithmetic over analyst
reports: bull case = supportive evidence mean, bear case = contrary
evidence mean, judges = weighted sums with a HOLD-by-default margin.
Ties and thin margins resolve to HOLD/NEUTRAL (fail-closed). Documented
in docs/ALPACATRADINGAGENT_PORT.md.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

EXECUTABLE = ("BUY", "HOLD", "SELL", "LONG", "NEUTRAL", "SHORT")

_PROPOSAL_RE = re.compile(r"FINAL TRANSACTION PROPOSAL:\s*\*{0,2}(BUY|SELL|HOLD|LONG|SHORT|NEUTRAL)\*{0,2}")
_PRICE_RE = re.compile(r"\$?\s*(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?")


@dataclass
class AnalystReport:
    source: str  # market | sentiment | news | fundamentals | macro
    score: float  # -1 (bearish) .. +1 (bullish)
    confidence: str = "medium"  # high | medium | low
    summary: str = ""

    def __post_init__(self):
        self.score = max(-1.0, min(1.0, float(self.score)))
        if self.confidence not in ("high", "medium", "low"):
            raise ValueError(f"bad confidence {self.confidence}")


@dataclass
class DebateResult:
    bull_case: float
    bear_case: float
    rounds: int
    judge: str  # bull | bear | tie
    margin: float


@dataclass
class TradeIntent:
    action: str  # BUY | HOLD | SELL (stocks-only port: no SHORT opens)
    symbol: str
    notional: float = 0.0
    stop_loss_price: float | None = None
    take_profit_price: float | None = None
    sizing_reason: str = ""
    safety_checks: dict[str, dict] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    paper: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {"action": self.action, "symbol": self.symbol, "notional": self.notional,
                "stop_loss_price": self.stop_loss_price, "take_profit_price": self.take_profit_price,
                "sizing_reason": self.sizing_reason, "safety_checks": self.safety_checks,
                "reasons": self.reasons, "paper": self.paper, "live": False}


def extract_signal(text: str) -> str:
    """Deterministic part of SignalProcessor.process_signal (no LLM fallback)."""
    content = (text or "").upper()
    m = _PROPOSAL_RE.search(content)
    if m:
        return m.group(1)
    tail = content[-100:]
    for action in ("LONG", "SHORT", "NEUTRAL", "BUY", "SELL", "HOLD"):
        if action in tail:
            return action
    return "HOLD"


def extract_protective_price(guidance: str | None) -> float | None:
    """Port of schemas.extract_protective_price: absolute level or None."""
    if not guidance:
        return None
    match = _PRICE_RE.search(guidance)
    if not match:
        return None
    tail = guidance[match.end():].lstrip()
    if tail.startswith("%") or tail.lower().startswith("percent"):
        return None
    try:
        price = float(f"{match.group(1).replace(',', '')}.{match.group(2) or '0'}")
    except ValueError:
        return None
    return price if price > 0 else None


def run_investment_debate(reports: list[AnalystReport], max_rounds: int = 1,
                          judge_margin: float = 0.15) -> DebateResult:
    """Bull/bear debate: alternating speakers, judge at count >= 2N."""
    bull_ev = [r.score for r in reports if r.score > 0]
    bear_ev = [-r.score for r in reports if r.score < 0]
    bull_case = sum(bull_ev) / len(bull_ev) if bull_ev else 0.0
    bear_case = sum(bear_ev) / len(bear_ev) if bear_ev else 0.0
    rounds = 0
    transcript: list[str] = []
    speaker = "bull"
    while rounds < 2 * max(1, max_rounds):
        transcript.append(speaker)
        speaker = "bear" if speaker == "bull" else "bull"
        rounds += 1
    margin = bull_case - bear_case
    judge = "bull" if margin > judge_margin else ("bear" if margin < -judge_margin else "tie")
    return DebateResult(bull_case, bear_case, rounds, judge, margin)


def run_risk_debate(action: str, risk_flags: list[str],
                    max_rounds: int = 1) -> dict[str, Any]:
    """Risky/safe/neutral rotation, judge at count >= 3N.

    Any safe objection (risk flag present) downgrades BUY->HOLD; with no
    flags the trader's action stands. Rotation order mirrors upstream:
    Risky -> Safe -> Neutral -> Risky ...
    """
    order = ["risky", "safe", "neutral"]
    transcript = [order[i % 3] for i in range(3 * max(1, max_rounds))]
    if action in ("BUY", "LONG") and risk_flags:
        return {"final": "HOLD", "downgraded": True, "objections": list(risk_flags),
                "transcript": transcript}
    return {"final": action, "downgraded": False, "objections": [],
            "transcript": transcript}


def build_intent(symbol: str, reports: list[AnalystReport], price: float,
                 sizer, equity: float, requested_notional: float,
                 guard=None, risk_guidance: str = "",
                 risk_flags: list[str] | None = None,
                 bars=None) -> TradeIntent:
    """Full pipeline: debate -> trader direction -> risk debate -> size -> guard."""
    debate = run_investment_debate(reports)
    direction = {"bull": "BUY", "bear": "SELL", "tie": "HOLD"}[debate.judge]
    risk = run_risk_debate(direction, risk_flags or [])
    action = risk["final"]
    # stocks-only: never open shorts; bearish becomes SELL-only-if-held else HOLD
    if action == "SELL":
        action = "SELL"  # caller interprets as close-only; never SHORT
    reasons = [f"debate={debate.judge} margin={debate.margin:.2f} rounds={debate.rounds}",
               f"bull={debate.bull_case:.2f} bear={debate.bear_case:.2f}"]
    if risk["downgraded"]:
        reasons.append("risk-downgrade: " + "; ".join(risk["objections"]))

    conf = "high" if abs(debate.margin) > 0.5 else ("medium" if abs(debate.margin) > 0.25 else "low")
    notional, stop, sizing_reason = 0.0, None, "HOLD requires no size"
    checks: dict[str, dict] = {}
    if action in ("BUY", "SELL"):
        from src.risk.alptrading_sizing import compute_atr
        atr = compute_atr(bars) if bars is not None else None
        decision = sizer.size_position(equity=equity, price=price, atr=atr,
                                       confidence=conf, requested_notional=requested_notional)
        sizing_reason = decision.reason
        if decision.approved:
            notional, stop = decision.notional, decision.stop_loss_price
        else:
            reasons.append("sizer-rejected: " + decision.reason)
            action = "HOLD"
            notional, stop = 0.0, None
    guided_stop = extract_protective_price(risk_guidance)
    if guided_stop and (stop is None or guided_stop > stop * 0.5):
        stop = guided_stop
        reasons.append(f"protective stop from guidance: {guided_stop}")
    if guard is not None and action == "BUY":
        verdict = guard.check_order(symbol, notional,
                                    account={"equity": equity, "last_equity": equity})
        checks = verdict.checks
        if not verdict.allowed:
            reasons.append("guard-blocked: " + "; ".join(verdict.reasons))
            action, notional, stop = "HOLD", 0.0, None
    return TradeIntent(action, symbol, notional, stop, None, sizing_reason, checks, reasons)
