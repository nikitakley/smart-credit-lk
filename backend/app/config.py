""""Конфигурация приложения из переменных окружения."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

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
    database_url: str = "postgresql+psyopg://credit:credit@localhost:5432/credit"


@lru_cache
def get_settings() -> Settings:
    return Settings()
