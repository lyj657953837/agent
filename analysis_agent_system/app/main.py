"""Analysis Agent System – FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from analysis_agent_system.app.config import settings
from analysis_agent_system.app.services.database import init_db
from analysis_agent_system.app.routers import data_router, task_router, result_router, validation_router, output_router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup & shutdown logic."""
    logger.info("Starting %s v%s", settings.APP_TITLE, settings.APP_VERSION)
    logger.info("LLM endpoint: %s  model: %s", settings.VLLM_API_BASE, settings.MODEL_NAME)
    logger.info("Database: %s@%s:%s/%s", settings.DB_USER, settings.DB_HOST, settings.DB_PORT, settings.DB_NAME)

    # Initialize database tables
    try:
        init_db()
        logger.info("Database tables initialized")
    except Exception as exc:
        logger.warning("Database init failed (tables may already exist): %s", exc)

    yield

    logger.info("Shutting down %s", settings.APP_TITLE)


# ------------------------------------------------------------------
# Create FastAPI application
# ------------------------------------------------------------------

app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# Register routers
# ------------------------------------------------------------------

app.include_router(data_router.router)
app.include_router(task_router.router)
app.include_router(result_router.router)
app.include_router(validation_router.router)
app.include_router(output_router.router)


# ------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/", tags=["System"])
async def root():
    return {
        "service": settings.APP_TITLE,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }
