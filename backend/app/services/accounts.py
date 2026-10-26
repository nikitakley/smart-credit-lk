"""Учётные записи: список для демо-входа и поиск при входе."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.errors import ApiError
from app.schemas.auth import TestAccount, User


def list_test_accounts(db: Session) -> list[TestAccount]:
    # Сначала клиенты, затем аналитик ("client" > "analyst" по алфавиту)
    query = select(models.Account).where(models.Account.is_active).order_by(models.Account.role.desc(), models.Account.id)
    return [
        TestAccount(id=a.id, role=a.role, inn=a.company_inn, name=a.name, hint=a.hint)
        for a in db.scalars(query)
    ]


def get_user(db: Session, account_id: str) -> User:
    account = db.get(models.Account, account_id)
    if account is None or not account.is_active:
        raise ApiError(404, "account_not_found", "Учётная запись не найдена")
    return User(account_id=account.id, role=account.role, name=account.name, inn=account.company_inn)
