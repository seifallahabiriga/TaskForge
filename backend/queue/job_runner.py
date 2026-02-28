import time
import logging
from typing import Any


logger = logging.getLogger(__name__)


class JobRunner:

    def __init__(self, db):
        # DB session passed from ExecutionService
        self.db = db

    def run(self, *, task_id: str, payload: dict[str, Any]) -> dict:
        """
        Simulated AI execution logic.

        Steps:
        1. Log execution start
        2. Sleep to simulate workload
        3. Return mock result
        """

        logger.info(f"[Worker] Starting execution for task {task_id}")

        # Simulate compute time
        time.sleep(2)

        # Dummy logic: echo payload + simple metadata
        result = {
            "task_id": task_id,
            "status": "processed",
            "input": payload,
            "output": {
                "message": "Mock inference completed",
                "processed_keys": list(payload.keys()),
            },
        }

        logger.info(f"[Worker] Completed execution for task {task_id}")

        return result