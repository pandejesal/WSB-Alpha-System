"""Adaptive TP Selector — LuxAlgo "Sign Post" concept.

Tracks per-exit-condition outcomes in a rolling window and
dynamically selects the best active TP level for each new order.
"""

from __future__ import annotations

import logging
from collections import deque
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AdaptiveTPSelector:
    """Maintains rolling hit-rate statistics for multiple TP levels
    and suggests the best one for each new position.
    """

    def __init__(
        self,
        n_tp_levels: int = 3,
        lookback_days: int = 20,
        labels: list[str] | None = None,
    ) -> None:
        self.n_tp_levels = n_tp_levels
        self.lookback_days = lookback_days
        self.labels = labels or [f"TP{i}" for i in range(n_tp_levels)]
        # Rolling window per TP level: deque of bool
        self._history: list[deque] = [deque(maxlen=lookback_days) for _ in range(n_tp_levels)]
        self._counts: list[int] = [0] * n_tp_levels
        self._wins: list[int] = [0] * n_tp_levels

    def record_outcome(self, tp_index: int, profitable: bool) -> None:
        if 0 <= tp_index < self.n_tp_levels:
            self._history[tp_index].append(bool(profitable))
            self._counts[tp_index] += 1
            if profitable:
                self._wins[tp_index] += 1

    def hit_rate(self, tp_index: int) -> float:
        hist = self._history[tp_index]
        if not hist:
            return 0.0
        return sum(1 for x in hist if x) / len(hist)

    def best_tp(self) -> int:
        rates = [self.hit_rate(i) for i in range(self.n_tp_levels)]
        # Prefer most frequent winner; default to 0 if no data
        return int(max(range(self.n_tp_levels), key=lambda i: rates[i])) if any(rates) else 0

    def select_tp(self, *args: Any, **kwargs: Any) -> int:
        return self.best_tp()


__all__ = ["AdaptiveTPSelector"]
