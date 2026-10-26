"""Поведение источников: задержка ответа, случайные сбои, недоступность, зависание.

У каждого источника своё поведение. Значения по умолчанию — из переменных окружения,
во время работы меняются через /admin/sources (например, чтобы показать на демо, как банк
переживает недоступность бюро кредитных историй).
"""

import asyncio
import random
from enum import StrEnum
from functools import lru_cache
from typing import Self

from pydantic import BaseModel, Field, ValidationError, model_validator

from simulator.config import get_settings
from simulator.errors import SourceError


class Source(StrEnum):
    egr = "egr"  # ЕГРЮЛ / ЕГРИП
    nbki = "nbki"  # бюро кредитных историй
    pb = "pb"  # ФНС «Прозрачный бизнес»


class Mode(StrEnum):
    normal = "normal"  # отвечает с задержкой; сбоит с вероятностью failure_rate
    error = "error"  # сразу отвечает 503 — сервис недоступен
    timeout = "timeout"  # «зависает» на MOCK_TIMEOUT_SECONDS, затем 504


class SourceBehavior(BaseModel):
    mode: Mode = Mode.normal
    latency_min_ms: int = Field(ge=0, le=60_000)
    latency_max_ms: int = Field(ge=0, le=60_000)
    failure_rate: float = Field(ge=0, le=1, description="Доля случайных ответов 503")

    @model_validator(mode="after")
    def check_latency(self) -> Self:
        if self.latency_min_ms > self.latency_max_ms:
            raise ValueError("latency_min_ms не может быть больше latency_max_ms")
        return self


class SourceBehaviorUpdate(BaseModel):
    """Частичное изменение: передаются только меняемые поля."""

    mode: Mode | None = None
    latency_min_ms: int | None = None
    latency_max_ms: int | None = None
    failure_rate: float | None = None


class Faults:
    def __init__(self) -> None:
        self.behaviors: dict[Source, SourceBehavior] = {}
        self.reset()

    def reset(self) -> None:
        settings = get_settings()
        self.behaviors = {
            source: SourceBehavior(
                latency_min_ms=settings.mock_latency_min_ms,
                latency_max_ms=settings.mock_latency_max_ms,
                failure_rate=settings.mock_failure_rate,
            )
            for source in Source
        }

    def update(self, source: Source, change: SourceBehaviorUpdate) -> SourceBehavior:
        merged = self.behaviors[source].model_dump() | change.model_dump(exclude_unset=True, exclude_none=True)
        try:
            behavior = SourceBehavior.model_validate(merged)  # повторная проверка всех правил вместе
        except ValidationError as exc:
            raise SourceError(400, "bad_request", exc.errors()[0]["msg"]) from exc
        self.behaviors[source] = behavior
        return behavior

    async def apply(self, source: Source) -> None:
        """Вызывается перед обработкой запроса к источнику."""
        behavior = self.behaviors[source]
        if behavior.mode == Mode.error:
            raise SourceError(503, "service_unavailable", "Сервис временно недоступен")
        if behavior.mode == Mode.timeout:
            # asyncio.sleep не блокирует сервер: другие запросы в это время обслуживаются
            await asyncio.sleep(get_settings().mock_timeout_seconds)
            raise SourceError(504, "gateway_timeout", "Превышено время ожидания ответа")

        await asyncio.sleep(random.uniform(behavior.latency_min_ms, behavior.latency_max_ms) / 1000)
        if random.random() < behavior.failure_rate:
            raise SourceError(503, "service_unavailable", "Сервис временно недоступен")


@lru_cache
def get_faults() -> Faults:
    return Faults()
