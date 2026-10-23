"""Точка входа API умного кредитного кабинета."""

from fastapi import FastAPI

from app.config import get_settings
from app.errors import register_error_handlers

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)
register_error_handlers(app)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": settings.app_version}
