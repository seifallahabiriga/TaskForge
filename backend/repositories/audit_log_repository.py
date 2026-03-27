from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.audit_log import AuditLog


class AuditLogRepository:

    async def create(
        self,
        db: AsyncSession,
        *,
        action: str,
        entity_type: str,
        user_id: str | None = None,
        entity_id: str | None = None,
        event_metadata: dict | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            event_metadata=event_metadata,
            ip_address=ip_address,
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        return log

    async def get_by_user(
        self,
        db: AsyncSession,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[AuditLog]:
        result = await db.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_entity(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[AuditLog]:
        result = await db.execute(
            select(AuditLog)
            .where(
                AuditLog.entity_type == entity_type,
                AuditLog.entity_id == entity_id,
            )
            .order_by(AuditLog.timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_action(
        self,
        db: AsyncSession,
        action: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[AuditLog]:
        result = await db.execute(
            select(AuditLog)
            .where(AuditLog.action == action)
            .order_by(AuditLog.timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()