from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.model_version import ModelVersion


class ModelVersionRepository:

    async def get_by_id(
        self,
        db: AsyncSession,
        model_version_id: str,
    ) -> ModelVersion | None:
        result = await db.execute(
            select(ModelVersion).where(ModelVersion.id == model_version_id)
        )
        return result.scalars().first()

    async def get_default_for_task_type(
        self,
        db: AsyncSession,
        task_type: str,
    ) -> ModelVersion | None:
        result = await db.execute(
            select(ModelVersion)
            .where(
                ModelVersion.task_type == task_type,
                ModelVersion.is_default == True,
                ModelVersion.is_active == True,
            )
        )
        return result.scalars().first()

    async def list_by_task_type(
        self,
        db: AsyncSession,
        task_type: str,
        active_only: bool = True,
    ) -> list[ModelVersion]:
        query = select(ModelVersion).where(ModelVersion.task_type == task_type)
        if active_only:
            query = query.where(ModelVersion.is_active == True)
        result = await db.execute(query.order_by(ModelVersion.created_at.desc()))
        return result.scalars().all()

    async def list_all(
        self,
        db: AsyncSession,
        active_only: bool = True,
    ) -> list[ModelVersion]:
        query = select(ModelVersion)
        if active_only:
            query = query.where(ModelVersion.is_active == True)
        result = await db.execute(query.order_by(ModelVersion.created_at.desc()))
        return result.scalars().all()

    async def deactivate(
        self,
        db: AsyncSession,
        model_version_id: str,
    ) -> ModelVersion | None:
        model_version = await self.get_by_id(db, model_version_id)
        if not model_version:
            return None

        model_version.is_active = False
        await db.commit()
        await db.refresh(model_version)
        return model_version