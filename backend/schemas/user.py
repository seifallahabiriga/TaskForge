from pydantic import BaseModel, EmailStr
from datetime import datetime
from uuid import UUID
from backend.core.enums import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    username: str
    role: UserRole
    is_admin: bool
    is_active: bool
    last_login_at: datetime | None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    username: str | None = None
    password: str | None = None