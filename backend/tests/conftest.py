"""Общие фикстуры тестов.

Тесты работают с настоящим PostgreSQL (тем же, что поднимает docker compose), но с отдельной
базой credit_test. Рабочая база разработчика (credit) не затрагивается.

Как это устроено:
  1) один раз за запуск: создать базу credit_test, если её нет, и применить миграции;
  2) перед каждым тестом, которому нужна база: загрузить справочники и демо-заявки заново,
     чтобы тесты не зависели друг от друга и от порядка запуска.
Unit-тесты (автомат статусов, реквизиты) базу не запрашивают и работают без неё.
"""

import os

from sqlalchemy.engine import make_url

# Адрес тестовой базы выставляем ДО импорта приложения: движок SQLAlchemy создаётся
# при импорте app.db.session и берёт адрес из настроек (переменная DATABASE_URL).
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://credit:credit@localhost:5432/credit_test"
)
_test_url = make_url(TEST_DATABASE_URL)
if not (_test_url.database or "").endswith("_test"):
    # Тесты удаляют все заявки — защита от случайного запуска на рабочей базе.
    # render_as_string() скрывает пароль звёздочками.
    raise RuntimeError(f"Имя тестовой базы должно оканчиваться на _test: {_test_url.render_as_string()}")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["DEMO_MODE"] = "true"
os.environ["DEMO_SHOW_SIGN_CODE"] = "true"
# Интеграции: без пауз между повторами; симулятор — без задержек и с тем же ключом, что у бэкенда
os.environ["INTEGRATION_BACKOFF_SECONDS"] = "0"
os.environ["INTEGRATION_API_KEY"] = os.environ["MOCKS_API_KEY"] = "test-mocks-key"
os.environ["MOCK_LATENCY_MIN_MS"] = os.environ["MOCK_LATENCY_MAX_MS"] = "0"
os.environ["MOCK_FAILURE_RATE"] = "0"

# Импорты приложения — только после настройки окружения выше
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.seed import reset_demo_applications, seed_reference_data
from app.db.session import SessionLocal, engine
from app.main import app

BACKEND_DIR = Path(__file__).resolve().parents[1]
MOCKS_DIR = BACKEND_DIR.parent / "mocks"


def alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["configure_logger"] = False  # не трогать логирование pytest (см. migrations/env.py)
    return config


def create_database_if_missing() -> None:
    url = make_url(TEST_DATABASE_URL)
    # Создать базу, будучи подключённым к ней же, нельзя — подключаемся к служебной базе postgres.
    # CREATE DATABASE не выполняется внутри транзакции, поэтому режим AUTOCOMMIT.
    admin_engine = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as connection:
            exists = connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database}
            )
            if not exists:
                name = connection.dialect.identifier_preparer.quote(url.database)
                connection.execute(text(f"CREATE DATABASE {name}"))
    finally:
        admin_engine.dispose()


@pytest.fixture(scope="session")
def database() -> Iterator[None]:
    """Один раз за запуск: тестовая база существует и её схема соответствует последней миграции."""
    try:
        create_database_if_missing()
    except OperationalError as exc:
        pytest.exit(
            f"PostgreSQL недоступен по адресу {make_url(TEST_DATABASE_URL).render_as_string()}.\n"
            "Запустите базу из корня репозитория: docker compose up -d postgres\n"
            f"Ошибка: {exc.orig}",
            returncode=1,
        )
    command.upgrade(alembic_config(), "head")
    yield
    engine.dispose()


@pytest.fixture
def demo_data(database: None) -> None:
    """Перед тестом: справочники и демо-заявки в исходном состоянии (как после POST /api/demo/reset)."""
    settings = get_settings()
    with SessionLocal() as session:
        seed_reference_data(session, settings.seed_dir)
        reset_demo_applications(session, settings.seed_dir)
        session.commit()


@pytest.fixture
def db(demo_data: None) -> Iterator[Session]:
    """Сессия базы для тестов, которые работают с сервисами и моделями напрямую, без HTTP."""
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client(demo_data: None) -> Iterator[TestClient]:
    """HTTP-клиент к приложению: запросы идут в FastAPI без запуска сервера."""
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, account_id: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"accountId": account_id})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['accessToken']}"}


@pytest.fixture
def prodmarket(client: TestClient) -> dict[str, str]:
    return login(client, "prodmarket")


@pytest.fixture
def analyst(client: TestClient) -> dict[str, str]:
    return login(client, "analyst")


@pytest.fixture(scope="session")
def simulator_app() -> FastAPI:
    """Код симулятора из папки mocks/ — тот же, что работает в контейнере mocks.

    Тесты бэкенда проверяют адаптеры против настоящего симулятора, а не против придуманных ответов:
    если формат ответа симулятора изменится, тесты бэкенда это заметят.
    """
    sys.path.insert(0, str(MOCKS_DIR))
    from simulator.main import app as simulator

    return simulator


@pytest.fixture
def simulator(simulator_app: FastAPI) -> Iterator[TestClient]:
    """HTTP-клиент к симулятору без сети. Подходит адаптерам вместо обычного клиента: это тот же httpx.Client."""
    from simulator.faults import get_faults

    get_faults().reset()  # поведение источников — в памяти: сбрасываем между тестами
    with TestClient(simulator_app, headers={"X-Api-Key": get_settings().integration_api_key}) as test_client:
        yield test_client
