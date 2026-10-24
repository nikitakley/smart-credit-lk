"""Точка входа API умного кредитного кабинета."""

import logging

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.errors import register_error_handlers
from app.api.routes import analyst, applications, auth, catalog, system

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

DESCRIPTION = """
API цифрового кредитного конвейера для малого и микробизнеса.

**Авторизация:**: `POST /api/auth/login` → кнопка [Authorize] → вставить `accessToken`.

**Формат ошибок:** `{"error": {"code", "message", "fields": [{"field", "code", "message"}]}}`.

**Статусы заявки:** `draft → submitted → validation → enrichment → scoring → [approved | counter_offer | manual_review | docs_requested | rejected] → signing → issued` (или `declined_by_client`).

> *Этап 1:* ответы формируются заглушками в памяти, конвейер обработки не запущен.
"""


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=DESCRIPTION,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)

    api = APIRouter(prefix="/api")
    for module in (system, auth, catalog, applications, analyst):
        api.include_router(module.router)
    app.include_router(api)
    return app


app = create_app()
