from typing import Annotated

from fastapi import APIRouter, Query

from app.db.session import DbSession
from app.errors import error_responses
from app.schemas.actions import AnalystDecisionRequest
from app.schemas.application import AnalystQueueItem, ApplicationAnalyst
from app.schemas.enums import ApplicationStatus
from app.security import AnalystUser
from app.services import analyst as service
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
    responses=error_responses(401, 403, 404, 409, 422),
)
def decide(
    application_id: str, body: AnalystDecisionRequest, user: AnalystUser, db: DbSession
) -> ApplicationAnalyst:
    return application_to_analyst(service.decide(db, user, application_id, body))
