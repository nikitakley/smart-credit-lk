"""Конфигурация приложения из переменных окружения (см. .env.example в корне репозитория)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Корень репозитория: backend/app/config.py → parents[2]
REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Smart Credit LK API"
    app_version: str = "0.1.0"
    environment: str = "local"

    # Демо-режим: список тестовых учеток, сброс демо-данных
    demo_mode: bool = True
    # Показывать код подписи в ответе API (для демонстрации)
    demo_show_sign_code: bool = True

    # Авторизация
    jwt_secret: str = "local-dev-secret-code-0123456789abcdef"
    jwt_algorithm: str = "HS256"
    jwt_ttl_minutes: int = 480

    # Подписание
    sign_code_ttl_seconds: int = 300
    sign_code_max_attempts: int = 3

    # Офферы
    offer_ttl_days: int = 7

    # CORS - нужен при запуске фронтенда без прокси
    cors_origins: list[str] = ["http://localhost:5173"]

    # База данных
    database_url: str = "postgresql+psycopg://credit:credit@localhost:5432/credit"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_connect_timeout_seconds: int = 3
    db_echo: bool = False  # печатать SQL-запросы в лог (для отладки)

    # Сиды: папка с JSON-файлами начальных и демо-данных
    seed_dir: Path = REPO_ROOT / "data" / "seed"

    # Внешние источники (локально и в Docker — симулятор mocks). У каждого источника свой адрес:
    # переход на настоящий сервис — смена адреса и ключа, без изменений в коде.
    egr_base_url: str = "http://localhost:8001/egr"
    nbki_base_url: str = "http://localhost:8001/nbki"
    pb_base_url: str = "http://localhost:8001/pb"
    integration_api_key: str = "local-mocks-key"
    # Ожидание ответа одной попытки, число повторов и пауза перед первым повтором (дальше — вдвое больше)
    integration_timeout_seconds: float = 3.0
    integration_retries: int = 2
    integration_backoff_seconds: float = 0.5


@lru_cache
def get_settings() -> Settings:
    return Settings()
