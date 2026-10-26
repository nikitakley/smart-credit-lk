"""Конечный автомат статусов заявки.

Единственное место, где меняется статус и пишется история заявки. Каждый переход:
  1) проверяется по таблице разрешённых переходов;
  2) записывается событием в историю (таймлайн для клиента и журнал аудита для банка).
Действия, которые не меняют статус (например, повторный запрос данных), тоже пишутся в историю —
через record_event: это не переход, поэтому таблица переходов для них не нужна.
"""

from app.db import models
from app.errors import conflict
from app.schemas.enums import Actor, EventKind
from app.schemas.enums import ApplicationStatus as S

# Из какого статуса в какие можно перейти
TRANSITIONS: dict[S, frozenset[S]] = {
    S.draft: frozenset({S.submitted}),
    S.submitted: frozenset({S.validation}),
    # проверка полноты: не хватает данных → запрос; стоп-фактор → отказ
    S.validation: frozenset({S.enrichment, S.docs_requested, S.rejected}),
    # обогащение: стоп-фактор → отказ; источник недоступен → специалисту
    S.enrichment: frozenset({S.scoring, S.rejected, S.manual_review}),
    S.scoring: frozenset({S.approved, S.counter_offer, S.rejected, S.manual_review, S.docs_requested}),
    S.manual_review: frozenset({S.approved, S.counter_offer, S.rejected, S.docs_requested}),
    # клиент ответил → снова на проверку; либо решение принимает специалист
    S.docs_requested: frozenset({S.validation, S.approved, S.counter_offer, S.rejected}),
    S.approved: frozenset({S.signing, S.declined_by_client}),
    S.counter_offer: frozenset({S.signing, S.declined_by_client}),
    S.signing: frozenset({S.issued}),
    # конечные статусы: дальше переходов нет
    S.rejected: frozenset(),
    S.issued: frozenset(),
    S.declined_by_client: frozenset(),
}

STATUS_LABELS: dict[S, str] = {
    S.draft: "Черновик",
    S.submitted: "Заявка подана",
    S.validation: "Проверяем заявку",
    S.enrichment: "Запрашиваем данные в БКИ и ФНС",
    S.scoring: "Оцениваем заявку",
    S.manual_review: "Рассматривает специалист",
    S.docs_requested: "Нужна дополнительная информация",
    S.approved: "Одобрено",
    S.counter_offer: "Контрпредложение",
    S.rejected: "Отказ",
    S.signing: "Подписание договора",
    S.issued: "Кредит выдан",
    S.declined_by_client: "Клиент отказался",
}


def can_transition(current: S, target: S) -> bool:
    return target in TRANSITIONS[current]


def transition(
    application: models.Application,
    target: S,
    actor: Actor,
    *,
    actor_account_id: str | None = None,
    note: str | None = None,
) -> None:
    """Перевести заявку в новый статус и записать событие. Недопустимый переход — ошибка 409."""
    current = application.status
    if not can_transition(current, target):
        raise conflict(
            "invalid_transition",
            f"Нельзя перевести заявку из статуса «{STATUS_LABELS[current]}» в «{STATUS_LABELS[target]}»",
        )
    application.status = target
    application.events.append(models.ApplicationEvent(
        kind=EventKind.status_changed, status=target, actor=actor, actor_account_id=actor_account_id, note=note,
    ))


def record_event(
    application: models.Application,
    kind: EventKind,
    actor: Actor,
    *,
    actor_account_id: str | None = None,
    note: str | None = None,
) -> None:
    """Записать в историю действие без смены статуса. Статус события — текущий статус заявки."""
    if kind == EventKind.status_changed:
        raise ValueError("Смена статуса записывается только через transition()")
    application.events.append(models.ApplicationEvent(
        kind=kind, status=application.status, actor=actor, actor_account_id=actor_account_id, note=note,
    ))
