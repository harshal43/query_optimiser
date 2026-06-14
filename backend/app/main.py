from __future__ import annotations
from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.utils.logging import setup_logging
from app.db.connection import open_pool, close_pool
from app.vector.index import load_indices, save_indices
from app.routers import health
from app.routers import queries
from app.routers import optimizations
from app.routers import stream
from app.routers import ab_tests
from app.routers import admin
from app.routers import analytics
from app.routers import teams
from app.services.polling import start_polling
from app.services.admin_config import load_config
from app.services.techniques import seed_techniques


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.log_level)
    load_config()
    await open_pool()
    load_indices()
    await seed_techniques()
    task = asyncio.create_task(start_polling())
    yield
    task.cancel()
    save_indices()
    await close_pool()


def create_app() -> FastAPI:
    app = FastAPI(title="SQS — Snowflake Query Optimizer", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api")
    app.include_router(queries.router, prefix="/api")
    app.include_router(optimizations.router, prefix="/api")
    app.include_router(stream.router, prefix="/api")
    app.include_router(ab_tests.router, prefix="/api")
    app.include_router(admin.router, prefix="/api")
    app.include_router(analytics.router, prefix="/api")
    app.include_router(teams.router, prefix="/api")
    return app


app = create_app()
