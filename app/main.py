"""FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings

settings = get_settings()
logging.basicConfig(level=settings.LOG_LEVEL)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan hook."""
    yield


app = FastAPI(
    title="ECB Exchange Rate Pipeline API",
    description="REST API for ECB euro foreign exchange reference rates",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(router)
