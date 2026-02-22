from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from core.config import settings


# Database Engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,        # Detect dead connections
    pool_size=30,              # Adjust for cloud instance size
    max_overflow=15,
    pool_timeout=30,
    echo=False
)

# Session Factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

# Dependency Injection (FastAPI)
def get_db():
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()