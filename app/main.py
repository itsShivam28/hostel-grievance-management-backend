import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app import models  # noqa: F401  (registers tables on Base.metadata)
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.database import Base, SessionLocal, engine
from app.routers import auth, student, warden
from app.services.urgency import run_periodic_urgency_check


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.create_tables_on_startup:
        Base.metadata.create_all(bind=engine)

    urgency_task: asyncio.Task[None] | None = None
    if settings.urgency_job_enabled:
        urgency_task = asyncio.create_task(
            run_periodic_urgency_check(
                SessionLocal,
                interval_seconds=settings.urgency_check_interval_minutes * 60,
            )
        )

    yield

    if urgency_task is not None:
        urgency_task.cancel()
        with suppress(asyncio.CancelledError):
            await urgency_task


def create_app() -> FastAPI:
    app = FastAPI(
        title="Hostel Grievance Management System",
        version="1.0.0",
        lifespan=lifespan,
    )
    register_exception_handlers(app)
    app.include_router(auth.router)
    app.include_router(student.router)
    app.include_router(warden.router)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
