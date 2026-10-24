from typing import Annotated

from fastapi import APIRouter, Header, status

from app.schemas.application import (
    ApplicationClient,
    ApplicationCreate,
    ApplicationSummary,
    ApplicationUpdate,
    InfoResponseRequest,
    SubmitRequest,
)
from app.schemas.actions import SignCodeResponse, SignRequest
from app.errors import error_responses
from app.security import ClientUser
from app.stubs import store
from app.stubs.data import COMPANIES

router = APIRouter(prefix="/applications", tags=["Заявки клиента"])

IdempotencyKey = Annotated[
    str | None,
    Header(alias="Idempotency-Key", description="Уникальный ключ запроса: повторная отправка не создаёт дубль"),
]


@router.get("", response_model=list[ApplicationSummary], summary="Мои заявки", responses=error_responses(401, 403))
def list_applications(user: ClientUser) -> list[ApplicationSummary]:
    return store.list_own(user)


@router.post(
    "",
    response_model=ApplicationClient,
    status_code=status.HTTP_201_CREATED,
    summary="Создать черновик заявки",
    description="Компания берётся из профиля клиента. Поля можно передать сразу или заполнять по шагам в PATCH.",
    responses=error_responses(401, 403, 422),
)
def create_application(body: ApplicationCreate, user: ClientUser) -> ApplicationClient:
    return store.create_draft(user, body, COMPANIES[user.inn])


@router.get(
    "/{application_id}",
    response_model=ApplicationClient,
    summary="Заявка (для клиентской стороны)",
    description="Для отслеживания статуса опрашивать раз в 2 секунды, пока статус в submitted / validation / enrichment / scoring.",
    responses=error_responses(401, 403, 404),
)
def get_application(application_id: str, user: ClientUser) -> ApplicationClient:
    return store.get_own(user, application_id)


@router.patch(
    "/{application_id}",
    response_model=ApplicationClient,
    summary="Сохранить изменения черновика",
    description="Передаются только изменённые поля. Вызывать при переходе между шагами мастера.",
    responses=error_responses(401, 403, 404, 409, 422),
)
def update_application(application_id: str, body: ApplicationUpdate, user: ClientUser) -> ApplicationClient:
    return store.update_draft(user, application_id, body)


@router.post(
    "/{application_id}/submit",
    response_model=ApplicationClient,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Отправить заявку в банк",
    description="Проверяет обязательные поля и согласия, переводит заявку в submitted. "
    "Дальше заявка обрабатывается асинхронно.",
    responses=error_responses(401, 403, 404, 409, 422),
)
def submit_application(
    application_id: str, body: SubmitRequest, user: ClientUser, idempotency_key: IdempotencyKey = None
) -> ApplicationClient:
    return store.submit(user, application_id, body, idempotency_key)


@router.post(
    "/{application_id}/info",
    response_model=ApplicationClient,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ответить на запрос дополнительной информации",
    description="Доступно в статусе docs_requested. После ответа заявка снова проходит проверку.",
    responses=error_responses(401, 403, 404, 409, 422),
)
def respond_info(application_id: str, body: InfoResponseRequest, user: ClientUser) -> ApplicationClient:
    return store.respond_info(user, application_id, body)


@router.post(
    "/{application_id}/offer/accept",
    response_model=ApplicationClient,
    summary="Принять предложение банка",
    description="Ошибки: no_offer, offer_expired (409). Переводит заявку в signing.",
    responses=error_responses(401, 403, 404, 409),
)
def accept_offer(application_id: str, user: ClientUser) -> ApplicationClient:
    return store.accept_offer(user, application_id)


@router.post(
    "/{application_id}/offer/decline",
    response_model=ApplicationClient,
    summary="Отказаться от предложения банка",
    responses=error_responses(401, 403, 404, 409),
)
def decline_offer(application_id: str, user: ClientUser) -> ApplicationClient:
    return store.decline_offer(user, application_id)


@router.post(
    "/{application_id}/sign/code",
    response_model=SignCodeResponse,
    summary="Получить код для подписания договора",
    description="Код живёт 5 минут, даётся 3 попытки. В демо-режиме код возвращается в ответе.",
    responses=error_responses(401, 403, 404, 409),
)
def request_sign_code(application_id: str, user: ClientUser) -> SignCodeResponse:
    return store.request_sign_code(user, application_id)


@router.post(
    "/{application_id}/sign",
    response_model=ApplicationClient,
    summary="Подписать договор кодом",
    description="Ошибки: invalid_code (422), not_signing / code_expired / code_attempts_exceeded (409). "
    "После подписания средства зачисляются на счёт, статус issued.",
    responses=error_responses(401, 403, 404, 409, 422),
)
def sign_contract(application_id: str, body: SignRequest, user: ClientUser) -> ApplicationClient:
    return store.sign(user, application_id, body.code)
