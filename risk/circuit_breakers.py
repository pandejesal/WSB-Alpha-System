from typing import Dict, Any
import logging

class CircuitBreaker:
    def __init__(self, max_drawdown_pct: float = 0.15, max_daily_loss_pct: float = 0.05):
        self.max_drawdown_pct = max_drawdown_pct
        self.max_daily_loss_pct = max_daily_loss_pct

    def check_safety(self, peak_equity: float, current_equity: float, daily_starting_equity: float) -> Dict[str, Any]:
        if peak_equity <= 0 or daily_starting_equity <= 0:
            return {"safe": True, "status": "No data."}

        drawdown = (peak_equity - current_equity) / peak_equity
        daily_loss = (daily_starting_equity - current_equity) / daily_starting_equity

        if drawdown >= self.max_drawdown_pct:
            return {"safe": False, "status": f"EMERGENCY HALT: Max Drawdown ({drawdown:.2%})", "action": "HALT_ALL_TRADING"}
        if daily_loss >= self.max_daily_loss_pct:
            return {"safe": False, "status": f"DAILY HALT: Daily Loss ({daily_loss:.2%})", "action": "HALT_DAILY_TRADING"}

        return {"safe": True, "status": "Safe"}
