from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_async_db
from backend.api.deps import get_current_user, require_admin
from backend.schemas.task import TaskCreate, TaskResponse, TaskStatusResponse
from backend.services.task_service import TaskService
from backend.core.exceptions import TaskExecutionError

from fastapi import Request
from backend.services.audit_log_service import AuditService
from backend.middleware.rate_limiter import limit_task_create, limit_task_read
from backend.api.deps import get_ip

router = APIRouter(prefix="/tasks", tags=["Tasks"])

task_service = TaskService()
audit_service = AuditService()


# ------------------------------------------------------------------ #
# Create Task                                                          #
# ------------------------------------------------------------------ #

@router.post("/", response_model=TaskResponse, status_code=201, dependencies=[Depends(limit_task_create)])
async def create_task(
    payload: TaskCreate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user),
):
    task = await task_service.create_task(
        db,
        user_id=str(current_user.id),
        name=payload.name,
        task_type=payload.task_type,
        input_payload=payload.input_payload,
        priority=payload.priority,
        model_version_id=payload.model_version_id,
    )

    await audit_service.log_task_created(
        db,
        user_id=str(current_user.id),
        task_id=str(task.id),
        task_type=str(task.task_type),
        ip_address=get_ip(request),
    )

    return task


# ------------------------------------------------------------------ #
# Get Task By ID                                                       #
# ------------------------------------------------------------------ #

@router.get("/{task_id}", response_model=TaskResponse, dependencies=[Depends(limit_task_read)])
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user),
):
    task = await task_service.get_task(db, task_id)

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if str(task.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return task


# ------------------------------------------------------------------ #
# Poll Task Status                                                     #
# ------------------------------------------------------------------ #

@router.get("/{task_id}/status", response_model=TaskStatusResponse, dependencies=[Depends(limit_task_read)])
async def get_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user),
):
    task = await task_service.get_task(db, task_id)

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if str(task.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return task


# ------------------------------------------------------------------ #
# List My Tasks                                                        #
# ------------------------------------------------------------------ #

@router.get("/user/me", response_model=list[TaskResponse], dependencies=[Depends(limit_task_read)])
async def get_user_tasks(
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user),
):
    return await task_service.get_user_tasks(db, user_id=str(current_user.id))


# ------------------------------------------------------------------ #
# Internal Lifecycle Endpoints (for Celery Workers)                              #
# ------------------------------------------------------------------ #

@router.post("/{task_id}/start", response_model=TaskResponse)
async def start_task(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_admin),
):
    task = await task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    try:
        result = await task_service.start_task_execution(db, task_id=task_id)

        await audit_service.log_admin_lifecycle_override(
            db,
            admin_id=str(current_user.id),
            task_id=task_id,
            action="start",
            ip_address=get_ip(request),
        )

        return result
    except TaskExecutionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_admin),
):
    task = await task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    try:
        result = await task_service.complete_task_execution(db, task_id=task_id)

        await audit_service.log_admin_lifecycle_override(
            db,
            admin_id=str(current_user.id),
            task_id=task_id,
            action="complete",
            ip_address=get_ip(request),
        )

        return result
    except TaskExecutionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/{task_id}/fail", response_model=TaskResponse)
async def fail_task(
    task_id: str,
    error_message: str,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_admin),
):
    task = await task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    try:
        result = await task_service.fail_task_execution(
            db, task_id=task_id, error_message=error_message
        )

        await audit_service.log_admin_lifecycle_override(
            db,
            admin_id=str(current_user.id),
            task_id=task_id,
            action="fail",
            ip_address=get_ip(request),
        )

        return result
    except TaskExecutionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/{task_id}/retry", response_model=TaskResponse)
async def retry_task(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_admin),
):
    task = await task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    try:
        result = await task_service.retry_task(db, task_id=task_id)

        await audit_service.log_admin_lifecycle_override(
            db,
            admin_id=str(current_user.id),
            task_id=task_id,
            action="retry",
            ip_address=get_ip(request),
        )

        return result
    except TaskExecutionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


# ------------------------------------------------------------------ #
# Delete Task                                                          #
# ------------------------------------------------------------------ #

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user),
):
    task = await task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if str(task.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    await task_service.task_repo.delete_task(db, task_id)