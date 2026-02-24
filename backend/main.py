from fastapi import FastAPI
from contextlib import asynccontextmanager

from backend.db.session import engine
from backend.db.base import Base
import backend.models 

from backend.api.routes.auth import router as auth_router
from backend.api.routes.task import router as task_router
from backend.api.routes.user import router as user_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown
    pass


app = FastAPI(
    title="TaskForge",
    version="0.1.0",
    lifespan=lifespan
)

# Register routers
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(task_router)

@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok"}