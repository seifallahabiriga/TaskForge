from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_async_db
from backend.api.deps import require_admin
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.schemas.audit_log import AuditLogResponse
from backend.middleware.rate_limiter import limit_default


router = APIRouter(prefix="/audit", tags=["Audit"])

audit_repo = AuditLogRepository()


# ------------------------------------------------------------------ #
# Admin only — all audit routes                                        #
# ------------------------------------------------------------------ #

@router.get("/user/{user_id}", response_model=list[AuditLogResponse], dependencies=[Depends(limit_default)])
async def get_user_audit_logs(
    user_id: str,
    db: AsyncSession = Depends(get_async_db),
    _: None = Depends(require_admin),
):
    return await audit_repo.get_by_user(db, user_id)


@router.get("/entity/{entity_type}/{entity_id}", response_model=list[AuditLogResponse], dependencies=[Depends(limit_default)])
async def get_entity_audit_logs(
    entity_type: str,
    entity_id: str,
    db: AsyncSession = Depends(get_async_db),
    _: None = Depends(require_admin),
):
    return await audit_repo.get_by_entity(db, entity_type, entity_id)


@router.get("/action/{action}", response_model=list[AuditLogResponse], dependencies=[Depends(limit_default)])
async def get_action_audit_logs(
    action: str,
    db: AsyncSession = Depends(get_async_db),
    _: None = Depends(require_admin),
):
    return await audit_repo.get_by_action(db, action)