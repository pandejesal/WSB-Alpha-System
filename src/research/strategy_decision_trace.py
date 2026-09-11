"""Decision Trace — LuxAlgo "Sign Post" textual equivalent.

Logs why each trade was entered/exited. Supports the strategy
self-audit concept from the Claude Mythos 5 lessons.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class DecisionTrace:
    """Records the reasoning behind each trade entry and exit for
    audit-trail / self-audit purposes.
    """

    def __init__(self, strategy_id: str = "default", output_dir: str = "docs/data/ops") -> None:
        self.strategy_id = strategy_id
        self.output_dir = output_dir
        self.entries: list[dict[str, Any]] = []
        self.exits: list[dict[str, Any]] = []

    def log_entry(self, date: Any, ticker: str, reason: dict[str, Any]) -> None:
        try:
            d = pd.to_datetime(date).isoformat() if date is not None else ""
        except Exception:
            d = str(date)
        self.entries.append({"date": d, "ticker": ticker, "reason": reason})

    def log_exit(self, date: Any, ticker: str, reason: dict[str, Any]) -> None:
        try:
            d = pd.to_datetime(date).isoformat() if date is not None else ""
        except Exception:
            d = str(date)
        self.exits.append({"date": d, "ticker": ticker, "reason": reason})

    def to_dict(self) -> dict[str, Any]:
        return {"strategy_id": self.strategy_id, "entries": self.entries, "exits": self.exits}

    def save(self) -> str:
        os.makedirs(self.output_dir, exist_ok=True)
        path = os.path.join(self.output_dir, f"decision_trace_{self.strategy_id}.json")
        try:
            with open(path, "w") as f:
                json.dump(self.to_dict(), f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Failed to save decision trace: {e}")
        return path

    @classmethod
    def load(cls, path: str) -> dict[str, Any]:
        with open(path) as f:
            return json.load(f)


__all__ = ["DecisionTrace"]
