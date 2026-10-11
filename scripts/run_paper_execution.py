import logging
import os
import sys

from src.execution.paper_executor import PaperExecutor
from src.gs_compat.calendar import is_business_day

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    if not os.path.exists("docs/data/ops/plan.json"):
        logger.warning("No plan.json found. Skipping paper execution.")
        sys.exit(0)

    # Market-calendar guard (audit finding F2): the scheduled workflow runs on
    # weekdays only, but the schedule is not a safety boundary — verify here
    # that today is actually an NYSE trading day before touching the broker.
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).date()
    if not is_business_day(today):
        logger.warning(f"{today} is not an NYSE trading day (weekend/holiday). Skipping paper execution.")
        sys.exit(0)

    executor = PaperExecutor()
    executor.execute_plan()

if __name__ == "__main__":
    main()
