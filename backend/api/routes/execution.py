from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_async_db
from backend.api.deps import get_current_user
from backend.schemas.execution import ExecutionResponse
from backend.services.execution_service import ExecutionService
from backend.services.task_service import TaskService


router = APIRouter(prefix="/executions", tags=["Executions"])
execution_service = ExecutionService()
task_service = TaskService()


# ------------------------------------------------------------------ #
# Get Execution By ID                                                  #
# ------------------------------------------------------------------ #

@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user),
):
    execution = await execution_service.get_execution(db, execution_id)
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    # Ownership check via task
    task = await task_service.get_task(db, str(execution.task_id))
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if str(task.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return execution


# ------------------------------------------------------------------ #
# Get Executions By Task ID                                            #
# ------------------------------------------------------------------ #

@router.get("/task/{task_id}", response_model=list[ExecutionResponse])
async def get_task_executions(
    task_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user),
):
    # Ownership check
    task = await task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if str(task.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return await execution_service.get_task_executions(db, task_id)