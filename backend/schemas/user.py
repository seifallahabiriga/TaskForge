from pydantic import BaseModel, EmailStr
from datetime import datetime
from backend.core.enums import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    role: UserRole
    is_active: bool
    last_login_at: datetime | None

    class Config:
        from_attributes = True