from backend.core.enums import TaskType
from backend.core.exceptions import TaskExecutionError


class JobRunner:
    """
    Pure computation executor.
    No DB access. No status management.
    Receives payload, returns result dict.
    Swap internals here when plugging in real ML inference.
    """

    @staticmethod
    def execute(*, task_id: str, task_type: str, payload: dict) -> dict:
        if task_type == TaskType.INFERENCE:
            return JobRunner._run_inference(payload)
        
        elif task_type == TaskType.ANALYSIS:
            return JobRunner._run_analysis(payload)
        
        else:
            raise TaskExecutionError(f"Unsupported task type: {task_type}")

    # ------------------------------------------------------------------ #
    # Handlers — replace these with real ML logic later                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _run_inference(payload: dict) -> dict:
        # Placeholder — swap for model_service.predict() later
        input_data = payload.get("input", {})
        return {
            "task_type": "inference",
            "output": f"mock inference result for input: {input_data}",
        }

    @staticmethod
    def _run_analysis(payload: dict) -> dict:
        numbers = payload.get("numbers", [])
        return {
            "task_type": "analysis",
            "output": sum(numbers),
        }
    



# TODO: When implementing real cloud AI execution, convert this method to async def.
# Use httpx (not requests) for HTTP calls — requests is sync and will block the event loop.
# Example: result = await httpx.AsyncClient().post("https://api.openai.com/...")
# Then in ExecutionService.run(), add await before JobRunner.execute(...)