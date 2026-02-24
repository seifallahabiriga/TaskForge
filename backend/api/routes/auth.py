from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.services.auth_service import AuthService
from backend.schemas.auth import (
    UserRegisterSchema,
    UserLoginSchema,
    TokenResponseSchema
)
from backend.api.deps import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

auth_service = AuthService()



# Register
@router.post("/register", response_model=TokenResponseSchema)
def register(
    payload: UserRegisterSchema,
    db: Session = Depends(get_db)
):
    try:
        return auth_service.register(
            db,
            email=payload.email,
            password=payload.password,
            username=payload.username
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Login
@router.post("/login", response_model=TokenResponseSchema)
def login(
    payload: UserLoginSchema,
    db: Session = Depends(get_db)
):
    try:
        return auth_service.login(
            db,
            email=payload.email,
            password=payload.password
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )


# Refresh Token
@router.post("/refresh", response_model=TokenResponseSchema)
def refresh(
    refresh_token: str,
):
    try:
        return auth_service.refresh_tokens(refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )