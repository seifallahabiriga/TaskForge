from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_async_db
from backend.api.deps import get_current_user
from backend.repositories.user_repository import UserRepository
from backend.schemas.user import UserResponse, UserUpdate


router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

user_repo = UserRepository()


# Get Current User
@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user = Depends(get_current_user),
):
    return current_user


# Update Current User
@router.patch("/me", response_model=UserResponse)
async def update_me(
    payload: UserUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user),
):
    updated_user = await user_repo.update_user(
        db,
        current_user,
        **payload.model_dump(exclude_unset=True)
    )

    return updated_user


# Delete Current User
@router.delete("/me")
async def delete_me(
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user),
):
    await user_repo.delete_user(db, current_user)

    return {"status": "deleted"}