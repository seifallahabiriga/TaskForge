from sqlalchemy.orm import Session
from backend.models.user import User


class UserRepository:

    def get_by_email(self, db: Session, email: str) -> User | None:
        return db.query(User).filter(User.email == email).first()


    def get_by_id(self, db: Session, user_id: int) -> User | None:
        return db.query(User).filter(User.id == user_id).first()


    def create_user(self, db: Session, *, email: str, hashed_password: str, username: str | None = None) -> User:
        user = User(
            email=email,
            hashed_password=hashed_password,
            username=username
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user
    
    def update_user(self, db: Session, user: User, **updates):
        for key, value in updates.items():
            setattr(user, key, value)

        db.commit()
        db.refresh(user)
        return user
    
    def delete_user(self, db: Session, user: User):
        db.delete(user)
        db.commit()

    def list_users(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(User).offset(skip).limit(limit).all()