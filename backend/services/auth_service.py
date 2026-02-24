from datetime import timedelta
from sqlalchemy.orm import Session

from backend.repositories.user_repository import UserRepository
from backend.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    validate_token_type,
)
from backend.core.config import settings


class AuthService:

    def __init__(self):
        self.user_repo = UserRepository()

    # Registration
    def register(
        self,
        db: Session,
        *,
        email: str,
        password: str,
        username: str | None = None
    ):
        # Check if user exists
        existing_user = self.user_repo.get_by_email(db, email)
        if existing_user:
            raise ValueError("User already exists")

        # Hash password
        hashed_password = hash_password(password)

        # Create user
        user = self.user_repo.create_user(
            db,
            email=email,
            password_hash=hashed_password,
            username=username
        )

        # Generate tokens
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    # Login
    def login(
        self,
        db: Session,
        *,
        email: str,
        password: str
    ):
        user = self.user_repo.get_by_email(db, email)

        if not user:
            raise ValueError("Invalid credentials")

        if not verify_password(password, user.hashed_password):
            raise ValueError("Invalid credentials")

        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    # Token Refresh
    def refresh_tokens(self, refresh_token: str):
        payload = decode_token(refresh_token)

        validate_token_type(payload, "refresh")

        user_id = payload.get("sub")

        access_token = create_access_token(str(user_id))
        new_refresh_token = create_refresh_token(str(user_id))

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }