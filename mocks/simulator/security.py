"""Доступ по ключу API и общая «обвязка» запросов к источникам."""

import hmac
from typing import Annotated

from fastapi import Depends, Security
from fastapi.params import Depends as DependsParam
from fastapi.security import APIKeyHeader

from simulator.config import get_settings
from simulator.errors import SourceError
from simulator.faults import Source, get_faults

api_key_header = APIKeyHeader(name="X-Api-Key", auto_error=False, description="Ключ доступа (MOCKS_API_KEY)")


def require_api_key(api_key: Annotated[str | None, Security(api_key_header)]) -> None:
    expected = get_settings().mocks_api_key
    # compare_digest сравнивает за постоянное время — по времени ответа ключ не подобрать
    if api_key is None or not hmac.compare_digest(api_key.encode(), expected.encode()):
        raise SourceError(401, "unauthorized", "Неверный или отсутствующий ключ API (заголовок X-Api-Key)")


def source_guard(source: Source) -> DependsParam:
    """Зависимость для роутера источника: сначала проверка ключа, затем задержка и сбои источника."""

    async def guard(_: Annotated[None, Depends(require_api_key)]) -> None:
        await get_faults().apply(source)

    return Depends(guard)
