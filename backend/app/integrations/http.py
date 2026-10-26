"""Вызов внешнего сервиса: таймауты, повторные попытки, единая обработка ошибок, трассировка."""

import logging
import time
import uuid
from collections.abc import Iterator
from typing import Annotated, Any, TypeVar

import httpx2 as httpx
from fastapi import Depends
from pydantic import BaseModel, ValidationError

from app.config import get_settings
from app.schemas.checks import UnavailableReason

logger = logging.getLogger(__name__)

M = TypeVar("M", bound=BaseModel)


class SourceUnavailable(Exception):
    """Источник не дал ответа: недоступен, не уложился во время или ответил ошибкой."""

    def __init__(self, source: str, reason: UnavailableReason, http_status: int | None = None) -> None:
        super().__init__(f"{source}: {reason}" + (f" (HTTP {http_status})" if http_status else ""))
        self.source = source
        self.reason = reason
        self.http_status = http_status


def make_client() -> httpx.Client:
    """HTTP-клиент для обращений к источникам. Закрывать после использования (with make_client() as client)."""
    settings = get_settings()
    return httpx.Client(
        # Подключение — не дольше секунды: если сервер не принимает соединение, ждать дольше бессмысленно
        timeout=httpx.Timeout(settings.integration_timeout_seconds, connect=1.0),
        headers={"X-Api-Key": settings.integration_api_key},
    )


def get_integration_client() -> Iterator[httpx.Client]:
    """Зависимость FastAPI: клиент на время запроса. В тестах подменяется (app.dependency_overrides)."""
    with make_client() as client:
        yield client


IntegrationClient = Annotated[httpx.Client, Depends(get_integration_client)]


def request_json(
    client: httpx.Client, source: str, method: str, url: str, *, json: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    """Выполнить запрос с повторами. Возвращает тело ответа; None — источник ответил 404 «сведений нет».

    Повторяем только то, что может пройти со второй попытки: таймаут, обрыв связи, 5xx, 429.
    Ошибки 4xx — это ошибка в нашем запросе (ключ, формат, согласие), повтор не поможет.
    """
    settings = get_settings()
    attempts = settings.integration_retries + 1
    # Один идентификатор на все попытки: по нему запрос находится в логах банка и в журнале источника
    request_id = str(uuid.uuid4())
    reason, http_status = UnavailableReason.connection_error, None

    for attempt in range(1, attempts + 1):
        started = time.perf_counter()
        try:
            response = client.request(method, url, json=json, headers={"X-Request-Id": request_id})
        except httpx.TimeoutException:  # проверяется раньше TransportError: это его частный случай
            reason, http_status = UnavailableReason.timeout, None
        except httpx.TransportError:
            reason, http_status = UnavailableReason.connection_error, None
        else:
            duration_ms = round((time.perf_counter() - started) * 1000)
            if response.status_code == 404:
                logger.info("%s %s → 404 за %d мс, request_id=%s", source, url, duration_ms, request_id)
                return None
            if response.is_success:
                logger.info("%s %s → %d за %d мс, request_id=%s",
                            source, url, response.status_code, duration_ms, request_id)
                try:
                    return response.json()
                except ValueError as exc:
                    raise SourceUnavailable(source, UnavailableReason.invalid_response, response.status_code) from exc
            http_status = response.status_code
            if http_status < 500 and http_status != 429:
                logger.error("%s %s → %d: %s, request_id=%s", source, url, http_status, response.text[:300], request_id)
                raise SourceUnavailable(source, UnavailableReason.request_rejected, http_status)
            reason = UnavailableReason.server_error

        logger.warning("%s: попытка %d из %d не удалась (%s%s), request_id=%s",
                       source, attempt, attempts, reason, f", HTTP {http_status}" if http_status else "", request_id)
        if attempt < attempts:
            # Экспоненциальная пауза: 0.5 с, 1 с, 2 с... — не добиваем и без того перегруженный сервис
            time.sleep(settings.integration_backoff_seconds * 2 ** (attempt - 1))

    raise SourceUnavailable(source, reason, http_status)


def parse_response(source: str, model: type[M], data: dict[str, Any]) -> M:
    """Разобрать ответ источника. Неожиданный формат — тоже недоступность, а не ошибка 500 у нас."""
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        logger.error("%s: неожиданный формат ответа: %s", source, exc.errors()[:3])
        raise SourceUnavailable(source, UnavailableReason.invalid_response) from exc
