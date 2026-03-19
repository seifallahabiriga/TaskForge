from sqlalchemy.ext.asyncio import AsyncSession

from backend.repositories.result_repository import ResultRepository
from backend.core.exceptions import (
    TaskNotFoundError,
    ResultNotFoundError,
)


class ResultService:

    def __init__(self):
        self.result_repo = ResultRepository()

    # ------------------------------------------------------------------ #
    # Store Result                                                         #
    # ------------------------------------------------------------------ #

    async def store_result(
        self,
        db: AsyncSession,
        *,
        task_id: str,
        execution_id: str | None = None,
        output_summary: dict | None = None,
        storage_path: str | None = None,
    ):
        return await self.result_repo.create_result(
            db,
            task_id=task_id,
            execution_id=execution_id,
            output_summary=output_summary,
            storage_path=storage_path,
        )

    # ------------------------------------------------------------------ #
    # Queries                                                             #
    # ------------------------------------------------------------------ #

    async def get_result_by_task(self, db: AsyncSession, *, task_id: str):
        result = await self.result_repo.get_by_task_id(db, task_id)
        if not result:
            raise ResultNotFoundError(f"No result found for task {task_id}")
        return result

    async def get_result_by_execution(self, db: AsyncSession, *, execution_id: str):
        result = await self.result_repo.get_by_execution_id(db, execution_id)
        if not result:
            raise ResultNotFoundError(f"No result found for execution {execution_id}")
        return result

    # ------------------------------------------------------------------ #
    # Deletion                                                            #
    # ------------------------------------------------------------------ #

    async def delete_result(self, db: AsyncSession, *, task_id: str):
        deleted = await self.result_repo.delete_result(db, task_id)
        if not deleted:
            raise ResultNotFoundError(f"No result found for task {task_id}")
        return deleted