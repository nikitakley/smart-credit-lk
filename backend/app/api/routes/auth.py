from fastapi import APIRouter, status

from app.config import get_settings
from app.schemas.enums import Role
from app.schemas.auth import LoginRequest, LoginResponse, Me, TestAccount, User
from app.errors import ApiError, error_responses
from app.security import CurrentUser, create_access_token
from app.stubs import store
from app.stubs.data import COMPANIES, TEST_ACCOUNTS

router = APIRouter(tags=["Авторизация"])


@router.get(
    "/auth/test-accounts",
    response_model=list[TestAccount],
    summary="Тестовые учетные записи (только в демо-режиме)",
    responses=error_responses(404),
)
def test_accounts() -> list[TestAccount]:
    if not get_settings().demo_mode:
        raise ApiError(404, "not_found", "Демо-режим выключен")
    return TEST_ACCOUNTS


@router.post(
    "/auth/login",
    response_model=LoginResponse,
    summary="Вход по тестовой учетной записи",
    description="Клиент уже обслуживается в банке, поэтому регистрации нет. "
    "Токен передается в заголовке `Authorization: Bearer <token>`.",
    responses=error_responses(404, 422),
)
def login(body: LoginRequest) -> LoginResponse:
    account = next((a for a in TEST_ACCOUNTS if a.id == body.account_id), None)
    if account is None:
        raise ApiError(404, "account_not_found", "Учетная запись не найдена")
    user = User(account_id=account.id, role=account.role, name=account.name, inn=account.inn)
    token, ttl = create_access_token(user)
    return LoginResponse(access_token=token, expires_in=ttl, user=user)


@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Выход из тестовой учетной записи",
    description="Токен без состояния: клиент удаляет его у себя.",
    responses=error_responses(401),
)
def logout(_: CurrentUser) -> None:
    return None


@router.get("/me", response_model=Me, summary="Текущий пользователь и его компания", responses=error_responses(401))
def me(user: CurrentUser) -> Me:
    if user.role == Role.client and user.inn:
        return Me(user=user, company=COMPANIES.get(user.inn), current_application_id=store.current_application_id(user.inn))
    return Me(user=user)
