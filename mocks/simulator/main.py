"""Симулятор внешних источников данных для кредитного конвейера.

Заменяет реальные сервисы (ЕГРЮЛ/ЕГРИП, НБКИ, ФНС «Прозрачный бизнес») локальной реализацией
с сохранением смысла интеграции: отдельный сетевой сервис, ключ доступа, свои форматы ответов,
задержки и сбои. Данные синтетические — из папки data/.
"""

import time
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from fastapi import FastAPI, Request, Response

from simulator.config import get_settings
from simulator.errors import register_error_handlers
from simulator.faults import Source
from simulator.journal import JournalEntry, get_journal
from simulator.routes import admin, egr, nbki, pb
from simulator.store import get_store

DESCRIPTION = """
Локальные заменители внешних сервисов. Все данные синтетические.

**Доступ:** заголовок `X-Api-Key` (переменная `MOCKS_API_KEY`) → кнопка *Authorize*.

**Поведение источников** меняется через `PUT /admin/sources/{source}`:
`normal` — ответ с задержкой, `error` — 503, `timeout` — зависание и 504.
"""

SOURCE_PREFIXES = {f"/{source.value}/": source for source in Source}


def create_app() -> FastAPI:
    settings = get_settings()
    get_store()  # загрузить и проверить данные при старте: ошибка в JSON остановит запуск сразу

    app = FastAPI(
        title="Smart Credit LK — симулятор внешних источников",
        version=settings.app_version,
        description=DESCRIPTION,
    )
    register_error_handlers(app)

    @app.middleware("http")
    async def journal(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Записать каждый запрос к источнику в журнал и вернуть X-Request-Id для сквозной трассировки."""
        source = next((s for prefix, s in SOURCE_PREFIXES.items() if request.url.path.startswith(prefix)), None)
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        if source is not None:
            get_journal().add(JournalEntry(
                at=datetime.now(UTC), source=source, method=request.method, path=request.url.path,
                status=response.status_code, duration_ms=round((time.perf_counter() - started) * 1000),
                request_id=request_id,
            ))
        return response

    @app.get("/health", tags=["Служебное"], summary="Проверка работоспособности")
    def health() -> dict[str, object]:
        store = get_store()
        return {
            "status": "ok",
            "version": settings.app_version,
            "records": {"egr": len(store.egr), "nbki": len(store.nbki), "pb": len(store.pb)},
        }

    for router in (egr.router, nbki.router, pb.router, admin.router):
        app.include_router(router)
    return app


app = create_app()
