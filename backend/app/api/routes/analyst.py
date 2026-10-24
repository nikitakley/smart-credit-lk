from typing import Annotated

from fastapi import APIRouter, Query

from app.schemas.enums import ApplicationStatus
from app.schemas.application import AnalystQueueItem, ApplicationAnalyst
from app.schemas.actions import AnalystDecisionRequest
from app.errors import error_responses
from app.security import AnalystUser
from app.stubs import store

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
    status: Annotated[ApplicationStatus | None, Query(description="Фильтр по статусу")] = None,
) -> list[AnalystQueueItem]:
    return store.analyst_queue(status)


@router.get(
    "/{application_id}",
    response_model=ApplicationAnalyst,
    summary="Карточка заявки (для банковской стороны)",
    responses=error_responses(401, 403, 404),
)
def card(application_id: str, _: AnalystUser) -> ApplicationAnalyst:
    return store.analyst_get(application_id)


@router.post(
    "/{application_id}/decision",
    response_model=ApplicationAnalyst,
    summary="Решение специалиста",
    description="Доступно в статусах `manual_review` и `docs_requested`. "
    "`approve` - одобрить запрошенное; `counter_offer` - сумма меньше запрошенной; "
    "`request_docs` - запросить информацию (infoItems); `reject` - отказ (reasonCode из справочника). "
    "Комментарий для клиента обязателен для всех действий, кроме approve.",
    responses=error_responses(401, 403, 404, 409, 422),
)
def decide(application_id: str, body: AnalystDecisionRequest, _: AnalystUser) -> ApplicationAnalyst:
    return store.analyst_decide(application_id, body)
