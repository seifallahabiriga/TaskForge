import asyncio
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from alembic.config import Config
from alembic import command

from backend.main import app
from backend.db.session import get_async_db

# ---------------------------------------------------------------------------
# Test database URLs.
#
# We derive both from a single env var so they are guaranteed to point at
# the same database. The async URL is used by SQLAlchemy; the sync URL is
# used by Alembic (which needs psycopg2, not asyncpg).
# ---------------------------------------------------------------------------
TEST_ASYNC_URL = os.environ["TEST_DATABASE_ASYNC_URL"]

# Derive the sync URL — replace the driver prefix only.
# This guarantees Alembic and the test engine always target the same DB.
TEST_SYNC_URL = TEST_ASYNC_URL.replace(
    "postgresql+asyncpg://", "postgresql+psycopg2://"
)

print(f"\n[conftest] Async URL : {TEST_ASYNC_URL}")
print(f"[conftest] Sync URL  : {TEST_SYNC_URL}\n")


# ---------------------------------------------------------------------------
# Session-scoped engine + Alembic migrations.
#
# We use a session-scoped fixture so migrations only run once per test run,
# not once per test. That keeps the suite fast without sacrificing fidelity.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def event_loop():
    """
    Provide a single event loop for the entire test session.

    pytest-asyncio creates a new loop per test by default, which causes
    "Future attached to a different loop" errors when session-scoped async
    fixtures share state with function-scoped tests. Overriding here pins
    everything to one loop.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_ASYNC_URL, echo=False)

    def run_migrations():
        alembic_cfg = Config("alembic.ini")
        # Explicitly set the URL — never let Alembic fall through to
        # alembic.ini or DATABASE_SYNC_URL which may point at the app DB.
        alembic_cfg.set_main_option("sqlalchemy.url", TEST_SYNC_URL)
        print(f"[alembic] Migrating: {TEST_SYNC_URL}")
        command.upgrade(alembic_cfg, "head")
        print("[alembic] Done.")

    await asyncio.get_event_loop().run_in_executor(None, run_migrations)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def test_session_factory(test_engine):
    return async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )


@pytest_asyncio.fixture
async def db_session(test_session_factory):
    async with test_session_factory() as session:
        await session.begin()
        try:
            yield session
        finally:
            await session.rollback()


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