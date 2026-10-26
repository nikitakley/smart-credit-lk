from fastapi import APIRouter, status

from app.config import get_settings
from app.db.session import DbSession
from app.errors import ApiError, error_responses
from app.schemas.auth import LoginRequest, LoginResponse, Me, TestAccount
from app.schemas.enums import Role
from app.security import CurrentUser, create_access_token
from app.services import accounts
from app.services import applications as applications_service
from app.services.mappers import company_to_schema

router = APIRouter(tags=["Авторизация"])


@router.get(
    "/auth/test-accounts",
    response_model=list[TestAccount],
    summary="Тестовые учётные записи (только в демо-режиме)",
    responses=error_responses(404),
)
def test_accounts(db: DbSession) -> list[TestAccount]:
    if not get_settings().demo_mode:
        raise ApiError(404, "not_found", "Демо-режим выключен")
    return accounts.list_test_accounts(db)


@router.post(
    "/auth/login",
    response_model=LoginResponse,
    summary="Вход по тестовой учётной записи",
    description="Клиент уже обслуживается в банке, поэтому регистрации нет. "
    "Токен передаётся в заголовке `Authorization: Bearer <token>`.",
    responses=error_responses(404, 422),
)
def login(body: LoginRequest, db: DbSession) -> LoginResponse:
    user = accounts.get_user(db, body.account_id)
    token, ttl = create_access_token(user)
    return LoginResponse(access_token=token, expires_in=ttl, user=user)


@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Выход",
    description="Токен без состояния: клиент просто удаляет его у себя.",
    responses=error_responses(401),
)
def logout(_: CurrentUser) -> None:
    return None


@router.get("/me", response_model=Me, summary="Текущий пользователь и его компания", responses=error_responses(401))
def me(user: CurrentUser, db: DbSession) -> Me:
    if user.role == Role.client and user.inn:
        return Me(
            user=user,
            company=company_to_schema(applications_service.get_company(db, user.inn)),
            current_application_id=applications_service.current_application_id(db, user.inn),
        )
    return Me(user=user)
