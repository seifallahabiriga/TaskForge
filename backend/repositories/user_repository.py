from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models.user import User


class UserRepository:

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalars().first()


    async def get_by_id(self, db: AsyncSession, user_id: int) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalars().first()


    async def create_user(self, db: AsyncSession, *, email: str, password_hash: str, username: str | None = None) -> User:
        user = User(
            email=email,
            password_hash=password_hash,
            username=username
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        return user
    
    async def update_user(self, db: AsyncSession, user: User, **updates):
        for key, value in updates.items():
            setattr(user, key, value)

        await db.commit()
        await db.refresh(user)
        return user
    
    async def delete_user(self, db: AsyncSession, user: User):
        await db.delete(user)
        await db.commit()

    async def list_users(self, db: AsyncSession, skip: int = 0, limit: int = 100):
        result = await db.execute(select(User).offset(skip).limit(limit))
        return result.scalars().all()