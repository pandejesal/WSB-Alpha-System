from typing import Dict, Any, List
import logging

class CircuitBreaker:
    """
    Account-level risk safeguards.
    """
    def __init__(self, max_drawdown_pct: float = 0.15, max_daily_loss_pct: float = 0.05):
        self.max_drawdown_pct = max_drawdown_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.logger = logging.getLogger(__name__)

    def check_safety(self, peak_equity: float, current_equity: float, daily_starting_equity: float) -> Dict[str, Any]:
        """
        Evaluates if trading should be halted.
        """
        if peak_equity <= 0 or daily_starting_equity <= 0:
            return {"safe": True, "status": "No historical equity data to evaluate."}

        drawdown = (peak_equity - current_equity) / peak_equity
        daily_loss = (daily_starting_equity - current_equity) / daily_starting_equity

        if drawdown >= self.max_drawdown_pct:
            msg = f"EMERGENCY HALT: Max Drawdown ({drawdown:.2%}) exceeded limit ({self.max_drawdown_pct:.2%})."
            self.logger.critical(msg)
            return {"safe": False, "status": msg, "action": "HALT_ALL_TRADING"}

        if daily_loss >= self.max_daily_loss_pct:
            msg = f"DAILY HALT: Daily Loss ({daily_loss:.2%}) exceeded limit ({self.max_daily_loss_pct:.2%})."
            self.logger.critical(msg)
            return {"safe": False, "status": msg, "action": "HALT_DAILY_TRADING"}

        return {"safe": True, "status": "Account within safe risk parameters.", "action": "CONTINUE"}
