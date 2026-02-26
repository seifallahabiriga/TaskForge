from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.api.deps import get_current_user
from backend.schemas.task import TaskCreate, TaskResponse, TaskStatusResponse
from backend.services.task_service import TaskService
from backend.core.exceptions import TaskNotFoundError, TaskExecutionError


router = APIRouter(prefix="/tasks", tags=["Tasks"])
task_service = TaskService()


# ------------------------------------------------------------------ #
# Create Task                                                          #
# ------------------------------------------------------------------ #

@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    task = task_service.create_task(
        db,
        user_id=str(current_user.id),
        name=payload.name,
        task_type=payload.task_type,
        input_payload=payload.input_payload,
        priority=payload.priority,
        model_version_id=payload.model_version_id,
    )
    return task


# ------------------------------------------------------------------ #
# Get Task By ID                                                       #
# ------------------------------------------------------------------ #

@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    task = task_service.get_task(db, task_id)

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if str(task.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return task


# ------------------------------------------------------------------ #
# Poll Task Status                                                     #
# ------------------------------------------------------------------ #

@router.get("/{task_id}/status", response_model=TaskStatusResponse)
def get_task_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    task = task_service.get_task(db, task_id)

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if str(task.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return task


# ------------------------------------------------------------------ #
# List My Tasks                                                        #
# ------------------------------------------------------------------ #

@router.get("/user/me", response_model=list[TaskResponse])
def get_user_tasks(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    return task_service.get_user_tasks(db, user_id=str(current_user.id))


# ------------------------------------------------------------------ #
# Internal Lifecycle Endpoints (for Celery Workers)                              #
# ------------------------------------------------------------------ #

@router.post("/{task_id}/start", response_model=TaskResponse)
def start_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    # Ownership check BEFORE mutation
    task = task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if str(task.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    try:
        return task_service.start_task_execution(db, task_id=task_id)
    except TaskExecutionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/{task_id}/complete", response_model=TaskResponse)
def complete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    task = task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if str(task.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    try:
        return task_service.complete_task_execution(db, task_id=task_id)
    except TaskExecutionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/{task_id}/fail", response_model=TaskResponse)
def fail_task(
    task_id: str,
    error_message: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    task = task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if str(task.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    try:
        return task_service.fail_task_execution(db, task_id=task_id, error_message=error_message)
    except TaskExecutionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/{task_id}/retry", response_model=TaskResponse)
def retry_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    task = task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if str(task.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    try:
        return task_service.retry_task(db, task_id=task_id)
    except TaskExecutionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


# ------------------------------------------------------------------ #
# Delete Task                                                          #
# ------------------------------------------------------------------ #

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    task = task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if str(task.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    task_service.task_repo.delete_task(db, task_id)
