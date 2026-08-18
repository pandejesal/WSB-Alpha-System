import os
import sys
import logging
from src.execution.paper_executor import PaperExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    if not os.path.exists("docs/data/ops/plan.json"):
        logger.warning("No plan.json found. Skipping paper execution.")
        sys.exit(0)

    executor = PaperExecutor()
    executor.execute_plan()

if __name__ == "__main__":
    main()
