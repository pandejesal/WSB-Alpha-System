"""AlpacaTradingAgent decision-memory port (markdown log + resolution, no ChromaDB).

Source: https://github.com/huygiatrng/AlpacaTradingAgent
  agents/utils/memory.py (FinancialSituationMemory) + TradingMemoryLog +
  graph/reflection.py concepts.

Ported idea: every completed decision is written to an append-only
markdown memory log and later RESOLVED with realized returns and a
reflection line, so the loop is cumulative across runs. Embeddings are
dropped (Mnemosyne already provides semantic recall in this repo);
lookup is by symbol/strategy recency. Helpers stay dependency-free.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DecisionMemoryLog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("# Decision Memory Log\n", encoding="utf-8")

    def record(self, symbol: str, action: str, strategy: str, price: float,
               notional: float, reasons: list[str]) -> int:
        entry_id = sum(1 for _ in self._entries()) + 1
        block = (f"\n## {entry_id} {symbol} {action} [{strategy}] {_now()}\n"
                 f"- entry: {price} notional: {notional}\n"
                 f"- reasons: {'; '.join(reasons)}\n"
                 f"- status: OPEN\n")
        with self.path.open("a", encoding="utf-8") as f:
            f.write(block)
        return entry_id

    def resolve(self, entry_id: int, exit_price: float,
                reflection: str = "") -> dict[str, Any]:
        text = self.path.read_text(encoding="utf-8")
        m = re.search(rf"## {entry_id} (\S+) (\S+) \[(.*?)\].*?\n- entry: ([\d.]+) notional: ([\d.]+)",
                      text)
        if not m:
            raise KeyError(f"entry {entry_id} not found")
        entry = float(m.group(4))
        realized = (exit_price / entry - 1) * 100 if entry else 0.0
        addition = (f"- exit: {exit_price} realized: {realized:.2f}%\n"
                    f"- reflection: {reflection}\n- status: CLOSED\n")
        # append resolution right after the entry's status line (first occurrence)
        anchor = "- status: OPEN\n"
        idx = text.find(anchor)
        if idx >= 0:
            text = text[:idx + len(anchor)] + addition + text[idx + len(anchor):]
        self.path.write_text(text, encoding="utf-8")
        return {"entry_id": entry_id, "realized_pct": round(realized, 2)}

    def stats(self, strategy: str | None = None) -> dict[str, float]:
        text = self.path.read_text(encoding="utf-8")
        realized = [float(x) for x in re.findall(r"realized: ([-\d.]+)%", text)]
        if strategy:
            blocks = re.split(r"(?m)^## \d+ \S+ \S+ \[", text)[1:]
            realized = []
            for b in blocks:
                if b.startswith(strategy + "]"):
                    m = re.search(r"realized: ([-\d.]+)%", b)
                    if m:
                        realized.append(float(m.group(1)))
        if not realized:
            return {"decisions": 0, "win_rate": 0.0, "avg_realized_pct": 0.0}
        wins = sum(1 for r in realized if r > 0)
        return {"decisions": len(realized), "win_rate": wins / len(realized),
                "avg_realized_pct": sum(realized) / len(realized)}

    def _entries(self):
        return re.findall(r"(?m)^## \d+ ", self.path.read_text(encoding="utf-8"))
