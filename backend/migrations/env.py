"""Окружение Alembic: как подключаться к базе и с какими моделями сравнивать схему."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.db import models  # noqa: F401
from app.db.base import Base

config = context.config

# Логирование из alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Адрес базы — из настроек приложения (переменная DATABASE_URL), а не из alembic.ini.
# Так у приложения и миграций один источник конфигурации.
config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("%", "%%"))

# Описание схемы, с которым Alembic сравнивает базу при --autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Режим offline: вывести SQL миграций в консоль, не подключаясь к базе (alembic upgrade --sql)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Обычный режим: подключиться к базе и применить миграции."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # миграции — разовая операция, пул соединений не нужен
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # замечать и изменения типов колонок
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
