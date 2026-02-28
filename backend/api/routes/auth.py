from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_async_db
from backend.schemas.user import UserCreate, UserLogin
from backend.schemas.auth import TokenResponse, RefreshTokenSchema
from backend.services.auth_service import AuthService
from backend.core.exceptions import (
    UserAlreadyExistsError,
    InvalidCredentialsError,
    InvalidTokenError,
)

router = APIRouter(prefix="/auth", tags=["Auth"])

auth_service = AuthService()


@router.post("/register", response_model=TokenResponse)
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await auth_service.register(
            db,
            email=payload.email,
            password=payload.password,
            username=payload.username,
        )

    except UserAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: UserLogin,
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await auth_service.login(
            db,
            email=payload.email,
            password=payload.password,
        )

    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshTokenSchema,
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await auth_service.refresh_tokens(
            db,
            refresh_token=payload.refresh_token,
        )

    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )