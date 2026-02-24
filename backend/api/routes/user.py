from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db.session import get_db
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
def get_me(
    current_user = Depends(get_current_user),
):
    return current_user


# Update Current User
@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    updated_user = user_repo.update_user(
        db,
        current_user,
        **payload.model_dump(exclude_unset=True)
    )

    return updated_user


# Delete Current User
@router.delete("/me")
def delete_me(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    user_repo.delete_user(db, current_user)

    return {"status": "deleted"}