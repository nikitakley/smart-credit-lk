"""Базовый класс ORM-моделей и общие типы колонок."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, MetaData, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Единые правила именования ограничений: 
# ix_ - индексы, uq_ - уникальность,
# fk_ - внешние ключи, pk_ - первичные ключи, ck_ - проверки.
# Alembic опирается на имена, поэтому они должны быть предсказуемыми.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# JSONB в PostgreSQL; в других СУБД - обычный JSON
JsonType = JSON().with_variant(JSONB(), "postgresql")


def enum_column(enum_cls: type[StrEnum]) -> Enum:
    """Перечисление хранится как VARCHAR с CHECK-ограничением, а не как ENUM-тип PostgreSQL:
    новое значение добавляется простой миграцией без пересоздания типа."""
    return Enum(
        enum_cls,
        native_enum=False,
        create_constraint=True,
        length=32,
        values_callable=lambda e: [member.value for member in e],
        name=enum_cls.__name__.lower(),
    )


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {
        datetime: DateTime(timezone=True),
        dict[str, Any]: JsonType,
        list[Any]: JsonType,
    }


class TimestampMixin:
    """Время создания и последнего изменения записи - проставляет сама база."""

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
