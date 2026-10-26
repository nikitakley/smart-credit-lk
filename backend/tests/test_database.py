"""Проверки слоя данных: миграции, сиды, ограничения базы, оптимистичная блокировка."""

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import ApiError
from app.services.common import commit, load_application
from app.db import models
from app.db.seed import seed_reference_data
from app.db.session import SessionLocal
from tests.conftest import alembic_config


def test_migrations_match_models(database: None) -> None:
    # Если поменяли модели и забыли создать миграцию — тест упадёт со списком отличий
    command.check(alembic_config())


def test_reference_seed_is_idempotent(db: Session) -> None:
    def count(model: type[models.Base]) -> int:
        return db.scalar(select(func.count()).select_from(model))

    before = {model: count(model) for model in (models.Product, models.Company, models.Account)}
    seed_reference_data(db, get_settings().seed_dir)  # повторная загрузка — обновление, не дубли
    db.commit()
    assert {model: count(model) for model in before} == before


def test_database_rejects_unknown_status(db: Session) -> None:
    # Статус хранится как строка, но CHECK-ограничение пускает только значения из enum
    with pytest.raises(IntegrityError):
        db.execute(text("UPDATE applications SET status = 'unknown' WHERE id = 'A-1020'"))
    db.rollback()


def test_new_application_number_continues_after_demo(client: TestClient, prodmarket: dict) -> None:
    # Последовательность сдвинута за последнюю демо-заявку A-1026 — номера не пересекаются
    response = client.post("/api/applications", json={}, headers=prodmarket)
    assert response.json()["id"] == "A-1027"


def test_data_survives_between_requests(client: TestClient, prodmarket: dict) -> None:
    app_id = client.post("/api/applications", json={"amount": 700_000}, headers=prodmarket).json()["id"]
    # Каждый запрос открывает новую сессию — значит, данные пришли из базы, а не из памяти
    assert client.get(f"/api/applications/{app_id}", headers=prodmarket).json()["amount"] == 700_000


def test_concurrent_update_is_rejected(db: Session) -> None:
    # Два параллельных запроса: две независимые сессии прочитали одну и ту же заявку
    with SessionLocal() as other:
        first = load_application(db, "A-1020")
        second = load_application(other, "A-1020")
        assert first is not None and second is not None
        assert first.version == second.version

        first.amount = 2_000_000
        commit(db)  # первый успел сохранить — версия в базе увеличилась
        assert first.version == second.version + 1

        second.amount = 3_000_000
        with pytest.raises(ApiError) as error:
            commit(other)  # второй опирается на устаревшую версию

    assert error.value.status_code == 409
    assert error.value.code == "concurrent_update"
    # Изменение первого запроса не перезаписано вторым
    saved = load_application(db, "A-1020")
    assert saved is not None and saved.amount == 2_000_000
