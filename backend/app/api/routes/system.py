from fastapi import APIRouter, status

from app.config import get_settings
from app.schemas.base import CamelModel
from app.errors import ApiError, error_responses
from app.stubs import store

router = APIRouter(tags=["Служебное"])


class Health(CamelModel):
    status: str
    version: str


@router.get("/health", response_model=Health, summary="Проверка работоспособности")
def health() -> Health:
    return Health(status="ok", version=get_settings().app_version)


@router.post(
    "/demo/reset",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Сбросить демо-данные (только в демо-режиме)",
    responses=error_responses(404),
)
def demo_reset() -> None:
    if not get_settings().demo_mode:
        raise ApiError(404, "not_found", "Демо-режим выключен")
    store.state.reset()
