from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.result import Result


class ResultRepository:

    async def create_result(
        self,
        db: AsyncSession,
        *,
        task_id: str,
        execution_id: str | None = None,
        output_summary: dict | None = None,
        storage_path: str | None = None,
    ) -> Result:

        result = Result(
            task_id=task_id,
            execution_id=execution_id,
            output_summary=output_summary,
            storage_path=storage_path,
        )

        db.add(result)
        await db.commit()
        await db.refresh(result)

        return result

    async def get_by_task_id(self, db: AsyncSession, task_id: str) -> Result | None:
        result = await db.execute(select(Result).where(Result.task_id == task_id))
        return result.scalars().first()

    async def get_by_execution_id(self, db: AsyncSession, execution_id: str) -> Result | None:
        result = await db.execute(select(Result).where(Result.execution_id == execution_id))
        return result.scalars().first()

    async def delete_result(self, db: AsyncSession, task_id: str) -> bool:
        result = await self.get_by_task_id(db, task_id)
        if not result:
            return False

        await db.delete(result)
        await db.commit()

        return True