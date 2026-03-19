from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_async_db
from backend.api.deps import get_current_user
from backend.schemas.result import ResultResponse
from backend.services.result_service import ResultService
from backend.services.task_service import TaskService
from backend.core.exceptions import ResultNotFoundError


router = APIRouter(prefix="/results", tags=["Results"])
result_service = ResultService()
task_service = TaskService()


# ------------------------------------------------------------------ #
# Get Result By Task ID                                                #
# ------------------------------------------------------------------ #

@router.get("/{task_id}", response_model=ResultResponse)
async def get_result(
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

    try:
        return await result_service.get_result_by_task(db, task_id=task_id)
    except ResultNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")


# ------------------------------------------------------------------ #
# Delete Result                                                        #
# ------------------------------------------------------------------ #

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_result(
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

    try:
        await result_service.delete_result(db, task_id=task_id)
    except ResultNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")