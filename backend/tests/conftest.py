import asyncio
import os
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from alembic.config import Config
from alembic import command

from backend.main import app
from backend.db.session import get_async_db

TEST_ASYNC_URL = os.environ["TEST_DATABASE_ASYNC_URL"]
TEST_SYNC_URL = TEST_ASYNC_URL.replace(
    "postgresql+asyncpg://", "postgresql+psycopg2://"
)

print(f"\n[conftest] Async URL : {TEST_ASYNC_URL}")
print(f"[conftest] Sync URL  : {TEST_SYNC_URL}\n")


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_ASYNC_URL, echo=False)

    def run_migrations():
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", TEST_SYNC_URL)
        print(f"[alembic] Migrating: {TEST_SYNC_URL}")
        command.upgrade(alembic_cfg, "head")
        print("[alembic] Done.")

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, run_migrations)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def test_session_factory(test_engine):
    return async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(test_session_factory):
    """Truncate all tables before each test so tests don't bleed into each other."""
    async with test_session_factory() as session:
        await session.execute(text(
            "TRUNCATE TABLE audit_logs, results, executions, tasks, workers, users, model_versions RESTART IDENTITY CASCADE"
        ))
        await session.commit()


@pytest_asyncio.fixture
async def db_session(test_session_factory):
    async with test_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_async_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def registered_user(client):
    response = await client.post(
        "/auth/register",
        json={
            "email": "testuser@example.com",
            "password": "TestPassword123!",
            "username": "testuser",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest_asyncio.fixture
async def auth_headers(client, registered_user):
    response = await client.post(
        "/auth/login",
        json={
            "email": "testuser@example.com",
            "password": "TestPassword123!",
        },
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}