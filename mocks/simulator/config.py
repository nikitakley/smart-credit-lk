"""Настройки симулятора из переменных окружения."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_version: str = "0.1.0"

    # Ключ доступа: настоящие сервисы тоже выдают ключ API, без него запрос отклоняется
    mocks_api_key: str = "local-mocks-key"

    # Задержка ответа по умолчанию для всех источников, мс (случайная в диапазоне)
    mock_latency_min_ms: int = 300
    mock_latency_max_ms: int = 1200
    # Доля случайных сбоев (0.0 — никогда, 1.0 — всегда): ответ 503
    mock_failure_rate: float = 0.0
    # Сколько «висит» запрос в режиме timeout, прежде чем вернуть 504
    mock_timeout_seconds: float = 30.0

    # Папка с синтетическими данными источников
    mock_data_dir: Path = Path(__file__).resolve().parents[1] / "data"


@lru_cache
def get_settings() -> Settings:
    return Settings()
