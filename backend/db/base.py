from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import UUID
import uuid


class Base(DeclarativeBase):
    pass


def generate_uuid():
    return str(uuid.uuid4())