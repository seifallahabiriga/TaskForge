from backend.core.enums import TaskType
from backend.core.exceptions import TaskExecutionError


class JobRunner:
    """
    Pure computation dispatcher.
    No DB access. No asyncio. No status management.
    Returns a coroutine — the caller (tasks.py) owns the single asyncio.run()
    and awaits it inside the existing event loop.
    """

    @staticmethod
    def get_coroutine(
        *,
        task_type: str,
        payload: dict,
        model_version_id: str | None = None,
    ):
        from backend.services.model_service import ModelService

        if task_type == TaskType.INFERENCE:
            return ModelService().run_inference(
                task_type=TaskType.INFERENCE,
                input_payload=payload,
                model_version_id=model_version_id,
            )

        elif task_type == TaskType.ANALYSIS:
            return ModelService().run_inference(
                task_type=TaskType.ANALYSIS,
                input_payload=payload,
                model_version_id=model_version_id,
            )

        else:
            raise TaskExecutionError(f"Unsupported task type: {task_type}")