"""Подключение к PostgreSQL: движок, фабрика сессий и зависимость для эндпоинтов."""

import logging
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()

# Движок - один на все приложение. Держит пул соединений с базой и создается "лениво":
# первое подключение произойдет при первом запросе.
engine = create_engine(
    _settings.database_url,
    pool_size=_settings.db_pool_size,
    max_overflow=_settings.db_max_overflow,
    pool_pre_ping=True,
    connect_args={"connect_timeout": _settings.db_connect_timeout_seconds},
    echo=_settings.db_echo
)

# Фабрика сессий
SessionLocal = sessionmaker(bind=engine, autoflash=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Зависимость FastAPI: открыть сессию на время запроса и гарантированно закрыть ее."""
    with SessionLocal() as session:
        yield session


DbSession = Annotated[Session, Depends(get_db)]


def check_database() -> bool:
    """Доступна ли БД: простейший запрос SELECT 1."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError as exc:
        logger.warning("Database is unavailable: %s", exc.__class__.__name__)
        return False
