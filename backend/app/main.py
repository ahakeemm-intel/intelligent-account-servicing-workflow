from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.database import init_db
from app.api.routes import health, requests, documents, checker


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    if settings.DB_TYPE == "sqlite":
        await init_db()  # Auto-create tables for local/SQLite mode
    yield
    # Shutdown (nothing to clean up for now)


def create_app() -> FastAPI:
    app = FastAPI(
        title="IASW — Intelligent Account Servicing Workflow",
        description="AI-assisted document verification for banking account change requests.",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(requests.router)
    app.include_router(documents.router)
    app.include_router(checker.router)

    return app


app = create_app()
