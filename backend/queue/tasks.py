import asyncio
import time

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.queue.celery_app import celery_app
from backend.core.config import settings
from backend.core.enums import TaskStatus
from backend.services.execution_service import ExecutionService
from backend.services.task_service import TaskService
from backend.services.result_service import ResultService
from backend.workers.worker_app.job_runner import JobRunner


@celery_app.task(
    bind=True,
    name="app.queue.tasks.execute_ai_task",
    max_retries=3,
    default_retry_delay=5,
)
def execute_ai_task(self, task_id: str, payload: dict):
    asyncio.run(_run_task(self, task_id, payload))


async def _run_task(task_self, task_id: str, payload: dict):

    # Fresh engine per task run — avoids event loop conflicts on retry
    engine = create_async_engine(settings.DATABASE_ASYNC_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    try:
        async with session_factory() as db:

            task_service = TaskService()
            execution_service = ExecutionService()
            result_service = ResultService()

            # worker_id is None until worker registration is implemented
            execution = await execution_service.create_execution(
                db,
                task_id=task_id,
                worker_id=None,
            )

            start_time = time.time()

            try:
                # Fetch current task status before transitioning
                task = await task_service.get_task(db, task_id)

                # Only transition to RUNNING if not already RUNNING (handles retries)
                if task.status != TaskStatus.RUNNING:
                    await task_service.start_task_execution(db, task_id=task_id)

                await execution_service.mark_execution_running(
                    db,
                    execution_id=str(execution.id),
                )

                # Delegate compute to job runner
                task = await task_service.get_task(db, task_id)

                result = JobRunner.execute(
                    task_id=task_id,
                    task_type=task.task_type,
                    payload=payload,
                )

                runtime_ms = int((time.time() - start_time) * 1000)

                # Transition task → SUCCESS
                await task_service.complete_task_execution(db, task_id=task_id)
                await execution_service.mark_execution_success(
                    db,
                    execution_id=str(execution.id),
                    runtime_ms=runtime_ms,
                )
                
                # Store result
                await result_service.store_result(
                    db,
                    task_id=task_id,
                    execution_id=str(execution.id),
                    output_summary=result if isinstance(result, dict) else {"output": result},
                )

                return result

            except task_self.MaxRetriesExceededError as exc:
                runtime_ms = int((time.time() - start_time) * 1000)

                await execution_service.mark_execution_failed(
                    db,
                    execution_id=str(execution.id),
                    error_message=str(exc),
                    runtime_ms=runtime_ms,
                )
                await task_service.fail_task_execution(
                    db,
                    task_id=task_id,
                    error_message=str(exc),
                )
                raise

            except Exception as exc:
                runtime_ms = int((time.time() - start_time) * 1000)

                await execution_service.mark_execution_failed(
                    db,
                    execution_id=str(execution.id),
                    error_message=str(exc),
                    runtime_ms=runtime_ms,
                )

                # Transition task → RETRYING before handing back to Celery
                await task_service.retry_task(db, task_id=task_id)
                raise task_self.retry(exc=exc)

    finally:
        await engine.dispose()