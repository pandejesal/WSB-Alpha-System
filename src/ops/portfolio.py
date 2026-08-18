from typing import List, Dict, Any

class PortfolioManager:
    """
    Manages sizing and target merging for the 7 equal-risk sleeves.
    Constraints:
      - 10% vol target per sleeve (not implemented in exact math here, but placeholders).
      - <= 60% max notional of the account in total.
      - 40% cash floor.
    """
    def __init__(self, account_equity: float, max_notional_pct: float = 0.60):
        self.account_equity = account_equity
        self.max_notional_pct = max_notional_pct
        self.sleeve_names = [
            "us_momentum_top5",
            "spy_sma200",
            "spy_rsi2",
            "btc_vol_target_sma100",
            "us_lowvol_top30",
            "us_pead_top5",
            "breakout_burst"
        ]

    def size_sleeve(self, sleeve_id: str, targets: List[Dict[str, Any]], prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Sizes targets for a single sleeve to its allowed nominal equal-risk equity.
        Nominal equal risk is account_equity * 0.60 / 7.
        """
        # Limit paper scaling
        capped_equity = min(self.account_equity, 100000.0)
        sleeve_equity = capped_equity * self.max_notional_pct / len(self.sleeve_names)

        if not targets:
            return []

        sized_targets = []
        for t in targets:
            ticker = t.get("symbol", t.get("ticker"))
            if not ticker or ticker not in prices:
                continue

            weight = t.get("notional_pct", 1.0 / len(targets))
            allocated_usd = sleeve_equity * weight
            qty = allocated_usd / prices[ticker]

            sized_targets.append({
                "sleeve_id": sleeve_id,
                "ticker": ticker,
                "qty": qty,
                "side": t.get("side", "buy"),
                "allocated_usd": allocated_usd
            })

        return sized_targets

    def merge_targets(self, all_sized_targets: List[Dict[str, Any]], strategy_ranks: Dict[str, int]) -> List[Dict[str, Any]]:
        """
        Merges same-ticker orders across sleeves.
        Issues order under the highest-ranked strategy's prefix.
        Distributes attribution (which we simply store here for downstream use).
        """
        merged = {}

        for t in all_sized_targets:
            ticker = t["ticker"]
            side = t["side"]
            key = f"{ticker}_{side}"

            if key not in merged:
                merged[key] = {
                    "ticker": ticker,
                    "side": side,
                    "qty": 0.0,
                    "sleeves": [],
                    "highest_rank": 9999,
                    "primary_sleeve": t["sleeve_id"]
                }

            merged[key]["qty"] += t["qty"]
            merged[key]["sleeves"].append({
                "sleeve_id": t["sleeve_id"],
                "qty": t["qty"]
            })

            rank = strategy_ranks.get(t["sleeve_id"], 9999)
            if rank < merged[key]["highest_rank"]:
                merged[key]["highest_rank"] = rank
                merged[key]["primary_sleeve"] = t["sleeve_id"]

        final_targets = []
        for v in merged.values():
            final_targets.append({
                "ticker": v["ticker"],
                "side": v["side"],
                "qty": v["qty"],
                "primary_sleeve": v["primary_sleeve"],
                "attributions": v["sleeves"]
            })

        return final_targets
