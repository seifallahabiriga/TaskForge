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
# Test database URL — override via env or fall back to a dedicated test DB.
# Never run tests against the application database.
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_ASYNC_URL"
)


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
    """
    Create the async engine and run Alembic migrations exactly once.

    We point Alembic at the test database by temporarily overriding the
    sqlalchemy.url in the config object — no file edits required.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Run migrations synchronously via Alembic's scripting API.
    # Alembic uses its own sync connection internally, which is fine here.
    def run_migrations():
        alembic_cfg = Config("alembic.ini")
        # Override the URL so Alembic targets the test DB, not production.
        alembic_cfg.set_main_option(
            "sqlalchemy.url",
            TEST_DATABASE_URL.replace("+asyncpg", "+psycopg2"),
        )
        command.upgrade(alembic_cfg, "head")

    # Run in a thread so we don't block the event loop.
    await asyncio.get_event_loop().run_in_executor(None, run_migrations)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def test_session_factory(test_engine):
    """Session factory bound to the test engine."""
    return async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )


# ---------------------------------------------------------------------------
# Function-scoped DB session with automatic rollback.
#
# Each test gets its own transaction that is rolled back after the test
# completes — leaving the database clean for the next test without needing
# to truncate tables or re-run migrations.
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def db_session(test_session_factory):
    """
    Yield a database session that rolls back after each test.

    The trick: we begin a savepoint (nested transaction) inside the outer
    transaction, run the test, then roll back to the savepoint. This works
    even for code that calls session.commit() internally — the outer
    transaction absorbs the commit and the rollback undoes it.
    """
    async with test_session_factory() as session:
        await session.begin()
        try:
            yield session
        finally:
            await session.rollback()


# ---------------------------------------------------------------------------
# HTTP client wired to the FastAPI app.
#
# ASGITransport lets httpx send requests directly to the ASGI app without
# spinning up a real HTTP server. We override the get_db dependency so
# routes use our test session (with rollback) instead of the real one.
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def client(db_session):
    """
    Async HTTP client that hits the FastAPI app in-process.

    Dependency override: get_db → yields the test session so all DB
    operations inside request handlers are part of the rollback transaction.
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_async_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Convenience fixtures
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def registered_user(client):
    """
    Register a test user and return the response payload.

    Tests that need an authenticated user should use this fixture rather
    than repeating the registration call.
    """
    payload = {
        "email": "testuser@example.com",
        "password": "TestPassword123!",
        "full_name": "Test User",
    }
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest_asyncio.fixture
async def auth_headers(client, registered_user):
    """
    Log in as the registered test user and return Authorization headers.

    Usage in tests:
        response = await client.get("/tasks/user/me", headers=auth_headers)
    """
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