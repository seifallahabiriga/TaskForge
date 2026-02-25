from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db.session import get_db
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
def register(
    payload: UserCreate,
    db: Session = Depends(get_db),
):
    try:
        return auth_service.register(
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
def login(
    payload: UserLogin,
    db: Session = Depends(get_db),
):
    try:
        return auth_service.login(
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
def refresh(
    payload: RefreshTokenSchema,
    db: Session = Depends(get_db),
):
    try:
        return auth_service.refresh_tokens(
            db,
            refresh_token=payload.refresh_token,
        )

    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )