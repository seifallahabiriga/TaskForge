from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.api.deps import get_current_user
from backend.schemas.task import TaskCreate, TaskResponse
from backend.services.task_service import TaskService
from backend.core.enums import TaskStatus



router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"]
)

task_service = TaskService()


# Create Task
@router.post("/", response_model=TaskResponse)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):

    return task_service.create_task(
        db,
        user_id=current_user.id,
        task_type=payload.task_type,
        payload=payload.payload
    )


# Get Task By ID
@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):

    task = task_service.get_task(db, task_id)

    if not task or task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return task

 
# List User Tasks
@router.get("/user/me", response_model=list[TaskResponse])
def get_user_tasks(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):

    return task_service.get_user_tasks(
        db,
        user_id=current_user.id
    )


# Start Task Execution
@router.post("/{task_id}/start")
def start_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):

    task = task_service.start_task_execution(
        db,
        task_id=task_id
    )

    if not task or task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return task


# Complete Task Execution
@router.post("/{task_id}/complete")
def complete_task(
    task_id: int,
    result: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):

    task = task_service.complete_task_execution(
        db,
        task_id=task_id,
        result=result
    )

    if not task or task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return task


# Fail Task Execution
@router.post("/{task_id}/fail")
def fail_task(
    task_id: int,
    error_message: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):

    task = task_service.fail_task_execution(
        db,
        task_id=task_id,
        error_message=error_message
    )

    if not task or task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return task


# Delete Task
@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):

    success = task_service.task_repo.delete_task(
        db,
        task_id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return {"status": "deleted"}