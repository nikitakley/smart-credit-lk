from typing import Annotated

from fastapi import APIRouter, Query

from app.db.session import DbSession
from app.errors import error_responses
from app.integrations.http import IntegrationClient
from app.schemas.actions import AnalystDecisionRequest
from app.schemas.application import AnalystQueueItem, ApplicationAnalyst
from app.schemas.enums import ApplicationStatus
from app.security import AnalystUser
from app.services import analyst as service
from app.services import enrichment
from app.services.mappers import application_to_analyst, application_to_queue_item

router = APIRouter(prefix="/analyst/applications", tags=["Сотрудник банка"])


@router.get(
    "",
    response_model=list[AnalystQueueItem],
    summary="Очередь заявок",
    description="Сортировка по дате создания, новые сверху. Черновики не показываются.",
    responses=error_responses(401, 403),
)
def queue(
    _: AnalystUser,
    db: DbSession,
    status: Annotated[ApplicationStatus | None, Query(description="Фильтр по статусу")] = None,
) -> list[AnalystQueueItem]:
    return [application_to_queue_item(a) for a in service.queue(db, status)]


@router.get(
    "/{application_id}",
    response_model=ApplicationAnalyst,
    summary="Карточка заявки (полная проекция)",
    responses=error_responses(401, 403, 404),
)
def card(application_id: str, _: AnalystUser, db: DbSession) -> ApplicationAnalyst:
    return application_to_analyst(service.get(db, application_id))


@router.post(
    "/{application_id}/decision",
    response_model=ApplicationAnalyst,
    summary="Решение специалиста",
    description="Доступно в статусах manual_review и docs_requested. "
    "approve — одобрить запрошенное; counter_offer — сумма меньше запрошенной; "
    "request_docs — запросить информацию (infoItems); reject — отказ (reasonCode из справочника). "
    "Комментарий для клиента обязателен для всех действий, кроме approve.",
    responses=error_responses(
        401, 403, 404, 409, 422, conflicts=("decision_not_allowed", "invalid_transition", "concurrent_update")
    ),
)
def decide(
    application_id: str, body: AnalystDecisionRequest, user: AnalystUser, db: DbSession
) -> ApplicationAnalyst:
    return application_to_analyst(service.decide(db, user, application_id, body))


@router.post(
    "/{application_id}/checks/refresh",
    response_model=ApplicationAnalyst,
    summary="Повторно запросить данные из источников",
    description="Запрашивает ЕГРЮЛ/ЕГРИП, НБКИ и «Прозрачный бизнес» и обновляет проверки заявки. "
    "Статус заявки не меняется; в историю пишется событие kind = checks_refreshed. "
    "Доступно в статусах enrichment, scoring, manual_review, docs_requested. "
    "Если источник не ответил, проверка получает статус unavailable — остальные данные всё равно сохраняются.",
    responses=error_responses(
        401, 403, 404, 409, conflicts=("checks_refresh_not_allowed", "not_submitted", "concurrent_update")
    ),
)
def refresh_checks(
    application_id: str, user: AnalystUser, db: DbSession, client: IntegrationClient
) -> ApplicationAnalyst:
    return application_to_analyst(enrichment.refresh_checks(db, user, application_id, client))
