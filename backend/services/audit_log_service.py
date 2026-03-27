from sqlalchemy.ext.asyncio import AsyncSession

from backend.repositories.audit_log_repository import AuditLogRepository


class AuditService:
    """
    Thin wrapper around AuditLogRepository.
    Each method maps to one auditable action — call these from routes
    and services after the main operation succeeds.
    Fire-and-forget: audit failures should never crash the main request.
    """

    def __init__(self):
        self.repo = AuditLogRepository()

    # ------------------------------------------------------------------ #
    # Auth events                                                          #
    # ------------------------------------------------------------------ #

    async def log_user_registered(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        ip_address: str | None = None,
    ):
        await self.repo.create(
            db,
            action="user.registered",
            entity_type="user",
            user_id=user_id,
            entity_id=user_id,
            ip_address=ip_address,
        )

    async def log_user_login(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        ip_address: str | None = None,
    ):
        await self.repo.create(
            db,
            action="user.login",
            entity_type="user",
            user_id=user_id,
            entity_id=user_id,
            ip_address=ip_address,
        )

    # ------------------------------------------------------------------ #
    # Task events                                                          #
    # ------------------------------------------------------------------ #

    async def log_task_created(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        task_id: str,
        task_type: str,
        ip_address: str | None = None,
    ):
        await self.repo.create(
            db,
            action="task.created",
            entity_type="task",
            user_id=user_id,
            entity_id=task_id,
            event_metadata={"task_type": task_type},
            ip_address=ip_address,
        )

    async def log_task_completed(
        self,
        db: AsyncSession,
        *,
        task_id: str,
        user_id: str | None = None,
    ):
        await self.repo.create(
            db,
            action="task.completed",
            entity_type="task",
            user_id=user_id,
            entity_id=task_id,
        )

    async def log_task_failed(
        self,
        db: AsyncSession,
        *,
        task_id: str,
        error_message: str,
        user_id: str | None = None,
    ):
        await self.repo.create(
            db,
            action="task.failed",
            entity_type="task",
            user_id=user_id,
            entity_id=task_id,
            event_metadata={"error": error_message},
        )

    # ------------------------------------------------------------------ #
    # Inference events                                                     #
    # ------------------------------------------------------------------ #

    async def log_inference_called(
        self,
        db: AsyncSession,
        *,
        task_id: str,
        provider: str,
        model_id: str,
        latency_ms: float,
        user_id: str | None = None,
    ):
        await self.repo.create(
            db,
            action="inference.called",
            entity_type="task",
            user_id=user_id,
            entity_id=task_id,
            event_metadata={
                "provider": provider,
                "model_id": model_id,
                "latency_ms": round(latency_ms, 1),
            },
        )

    # ------------------------------------------------------------------ #
    # Admin events                                                         #
    # ------------------------------------------------------------------ #

    async def log_admin_lifecycle_override(
        self,
        db: AsyncSession,
        *,
        admin_id: str,
        task_id: str,
        action: str,
        ip_address: str | None = None,
    ):
        await self.repo.create(
            db,
            action="admin.lifecycle_override",
            entity_type="task",
            user_id=admin_id,
            entity_id=task_id,
            event_metadata={"override_action": action},
            ip_address=ip_address,
        )