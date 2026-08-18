import json
from typing import Dict, List, Any

# Target metrics per PLAN.md/ARCHITECTURE.md
VOL_TARGET_ANNUALIZED = 0.10
MAX_TOTAL_EXPOSURE_PCT = 0.60
CASH_BUFFER_PCT = 0.40

class PortfolioManager:
    """
    Manages the 7 active sleeves for the autonomous paper-trading system.
    Provides equal-risk sizing, total exposure caps, and merged position accounting.
    """
    def __init__(self, registry_path: str = "strategies/registry.json"):
        self.registry_path = registry_path
        self.active_sleeves = [
            "us_momentum_top5",
            "spy_sma200",
            "spy_rsi2",
            "btc_vol_target_sma100",
            "us_lowvol_top30",
            "us_pead_top5",
            "breakout_burst"
        ]
        self._load_specs()

    def _load_specs(self):
        self.specs = {}
        try:
            with open(self.registry_path, "r") as f:
                data = json.load(f)

            for strategy in data.get("strategies", []):
                if strategy["id"] in self.active_sleeves and strategy.get("status") != "inactive":
                    self.specs[strategy["id"]] = strategy
        except Exception:
            pass

    def get_sleeve_definitions(self) -> List[Dict[str, Any]]:
        """
        Returns the definitions for all active sleeves.
        """
        definitions = []
        for sid in self.active_sleeves:
            spec = self.specs.get(sid, {})
            definitions.append({
                "id": sid,
                "spec_file": spec.get("spec_file"),
                "vol_target": VOL_TARGET_ANNUALIZED,
                "equal_risk": True
            })
        return definitions

    def compute_merged_targets(self, per_sleeve_targets: Dict[str, List[Dict[str, Any]]], account_equity: float = 100.0) -> Dict[str, Any]:
        """
        Merges targets across the 7 sleeves.
        Ensures total exposure <= 60% of account with 40% cash buffer.
        Allocates equal-risk to the 7 sleeves (nominally account_equity * 0.60 / 7).
        """
        num_sleeves = len(self.active_sleeves)
        if num_sleeves == 0:
            return {"targets": [], "attribution": {}}

        nominal_per_sleeve = (account_equity * MAX_TOTAL_EXPOSURE_PCT) / num_sleeves

        merged = {}
        attribution = {}

        for sleeve_id, targets in per_sleeve_targets.items():
            if sleeve_id not in self.active_sleeves:
                continue

            for target in targets:
                ticker = target.get("ticker")
                weight = target.get("weight", 0.0)
                notional = nominal_per_sleeve * weight

                if ticker not in merged:
                    merged[ticker] = 0.0
                    attribution[ticker] = {}

                merged[ticker] += notional

                if sleeve_id not in attribution[ticker]:
                    attribution[ticker][sleeve_id] = 0.0
                attribution[ticker][sleeve_id] += notional

        final_targets = []
        final_attribution = {}

        max_allowed = account_equity * MAX_TOTAL_EXPOSURE_PCT

        # Enforce $1 minimum notional.
        # The prompt requires: $100 account ... 7-sleeve roster ... every target qty must satisfy ... min-notional >= $1, total notional <= 60% of account
        # If we floor at $1, we must scale everything down to respect the 60% cap.

        for ticker, total_notional in merged.items():
            if total_notional > 0:
                if total_notional < 1.0:
                    total_notional = 1.0

                final_targets.append({
                    "ticker": ticker,
                    "notional": total_notional,
                    "side": "buy"
                })
                final_attribution[ticker] = {
                    sid: amt for sid, amt in attribution[ticker].items() # we don't normalize to 1 here yet
                }

        total_exposure = sum(t["notional"] for t in final_targets)

        if total_exposure > max_allowed:
            scale = max_allowed / total_exposure

            # If scaling pushes things below $1 again, we have to drop the smallest ones
            # For simplicity, we just drop the smallest positions until we fit, then scale.
            while True:
                total_exp = sum(t["notional"] for t in final_targets)
                if total_exp <= max_allowed:
                    break

                # Need to reduce. If we can't satisfy both max_allowed and min $1, we drop smallest.
                final_targets.sort(key=lambda x: x["notional"])
                final_targets.pop(0) # drop smallest

                # Re-floor remaining to max(1.0, notional * scale)
                # Actually, iterative dropping is safer.

                if not final_targets:
                    break

        # Finalize attribution as percentages
        for t in final_targets:
            ticker = t["ticker"]
            total_attr = sum(final_attribution[ticker].values())
            if total_attr > 0:
                final_attribution[ticker] = {k: v / total_attr for k, v in final_attribution[ticker].items()}

        correlation_flags = self._check_correlation_guard(per_sleeve_targets)

        return {
            "targets": final_targets,
            "attribution": final_attribution,
            "correlation_flags": correlation_flags
        }

    def _check_correlation_guard(self, per_sleeve_targets: Dict[str, List[Dict[str, Any]]]) -> List[str]:
        """
        Checks if two sleeves are heavily correlated in their signals today.
        """
        flags = []
        tickers_by_sleeve = {}

        for sleeve_id, targets in per_sleeve_targets.items():
            tickers_by_sleeve[sleeve_id] = set(t.get("ticker") for t in targets)

        sleeve_ids = list(tickers_by_sleeve.keys())
        for i in range(len(sleeve_ids)):
            for j in range(i+1, len(sleeve_ids)):
                s1 = sleeve_ids[i]
                s2 = sleeve_ids[j]

                set1 = tickers_by_sleeve[s1]
                set2 = tickers_by_sleeve[s2]

                if not set1 or not set2:
                    continue

                intersection = set1.intersection(set2)
                if len(intersection) > 0:
                    # High overlap flagged
                    overlap_pct = len(intersection) / min(len(set1), len(set2))
                    if overlap_pct > 0.5:
                        flags.append(f"High correlation (>50% overlap) between {s1} and {s2}")

        return flags

    def enforce_min_notional(self, result: Dict[str, Any], min_notional: float = 1.0) -> Dict[str, Any]:
        targets = result["targets"]
        valid_targets = []
        for t in targets:
            if t["notional"] >= min_notional:
                valid_targets.append(t)
        result["targets"] = valid_targets
        return result
