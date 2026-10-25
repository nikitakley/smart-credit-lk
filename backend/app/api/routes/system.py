from fastapi import APIRouter, Response, status

from app.config import get_settings
from app.schemas.base import CamelModel
from app.errors import ApiError, error_responses
from app.db.seed import reset_demo_applications, seed_reference_data
from app.db.session import DbSession, check_database

router = APIRouter(tags=["Служебное"])


class Health(CamelModel):
    status: str
    version: str
    database: str


@router.get(
    "/health",
    response_model=Health, 
    summary="Проверка работоспособности",
    description="200 - сервис и база доступны; 503 - база недоступна. Используется healthcheck Docker.",
    responses={503: {"model": Health, "description": "База данных недоступна"}},
)
def health(response: Response) -> Health:
    database_ok = check_database()
    if not database_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return Health(
        status="ok" if database_ok else "degraded",
        version=get_settings().app_version,
        database="ok" if database_ok else "unavailale",
    )


@router.post(
    "/demo/reset",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Сбросить демо-данные (только в демо-режиме)",
    description="Удаляет все заявки и заново загружает справочники и демо-заявки из data/seed.",
    responses=error_responses(404),
)
def demo_reset(db: DbSession) -> None:
    settings = get_settings()
    if not settings.demo_mode:
        raise ApiError(404, "not_found", "Демо-режим выключен")
    seed_reference_data(db, settings.seed_dir)
    reset_demo_applications(db, settings.seed_dir)
    db.commit()
