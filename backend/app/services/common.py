"""Общие помощники сервисов: загрузка заявки со связями и сохранение изменений."""

from datetime import UTC, datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.orm.exc import StaleDataError

from app.errors import conflict
from app.db import models

# Какие связи заявки подгружать сразу. Без этого SQLAlchemy делал бы отдельный запрос
# при каждом обращении к app.events, app.offers и т. д. (проблема «N+1 запросов»).
APPLICATION_LOAD_OPTIONS = (
    joinedload(models.Application.company),
    joinedload(models.Application.product),
    joinedload(models.Application.contract),
    selectinload(models.Application.events),
    selectinload(models.Application.checks),
    selectinload(models.Application.scoring_results),
    selectinload(models.Application.decisions),
    selectinload(models.Application.info_requests),
    selectinload(models.Application.offers),
)


def now() -> datetime:
    return datetime.now(UTC)


def application_query() -> Select[tuple[models.Application]]:
    return select(models.Application).options(*APPLICATION_LOAD_OPTIONS)


def load_application(db: Session, application_id: str) -> models.Application | None:
    query = (
        application_query()
        .where(models.Application.id == application_id)
        # перечитать объект из базы, даже если он уже есть в сессии: после commit
        # поля вроде updated_at и created_at новых событий проставила сама база
        .execution_options(populate_existing=True)
    )
    return db.scalars(query).first()


def commit(db: Session) -> None:
    """Сохранить изменения одной транзакцией.

    Если заявку за это время успел изменить кто-то другой (другой запрос, конвейер),
    оптимистичная блокировка даст StaleDataError — отвечаем 409, клиент обновит данные.
    """
    try:
        db.commit()
    except StaleDataError as exc:
        db.rollback()
        raise conflict(
            "concurrent_update", "Заявку только что изменили — обновите страницу и повторите действие"
        ) from exc