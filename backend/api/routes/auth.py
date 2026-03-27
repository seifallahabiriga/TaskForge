from fastapi import APIRouter, Depends, HTTPException, status, Request
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
from backend.services.audit_log_service import AuditService
from backend.api.deps import get_ip

router = APIRouter(prefix="/auth", tags=["Auth"])

audit_service = AuditService()
auth_service = AuthService()


@router.post("/register", response_model=TokenResponse)
async def register(
    payload: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
):
    try:
        result = await auth_service.register(
            db=db,
            email=payload.email,
            password=payload.password,
            username=payload.username,
        )

        await audit_service.log_user_registered(
            db=db,
            user_id=str(result["user"].id),
            ip_address=get_ip(request),
        )

        return result

    except UserAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

@router.post("/login", response_model=TokenResponse)
async def login(
    payload: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
):
    try:
        result = await auth_service.login(
            db,
            email=payload.email,
            password=payload.password,
        )

        await audit_service.log_user_login(
            db,
            user_id=str(result["user"].id),
            ip_address=get_ip(request),
        )

        return result

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
            refresh_token=payload.refresh_token
        )

    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )