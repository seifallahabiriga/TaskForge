from fastapi import FastAPI
from contextlib import asynccontextmanager

from backend.db.session import async_engine, sync_engine
from backend.db.base import Base

# ensures Celery tasks are registered on startup
import backend.queue.tasks  # noqa

from backend.api.routes.auth import router as auth_router
from backend.api.routes.task import router as task_router
from backend.api.routes.user import router as user_router
from backend.api.routes.result import router as result_router
from backend.api.routes.execution import router as execution_router

from backend.queue.redis_client import init_redis, close_redis
from backend.monitoring.health import router as health_router
from backend.monitoring.metrics import router as metrics_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=sync_engine)

    await init_redis()

    import backend.queue.celery_app  # noqa
    yield

    # Shutdown
    await close_redis()


app = FastAPI(
    title="TaskForge",
    version="0.1.0",
    lifespan=lifespan,
)

# Register routers
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(task_router)
app.include_router(result_router)
app.include_router(execution_router)

# Monitoring
app.include_router(health_router)
app.include_router(metrics_router)