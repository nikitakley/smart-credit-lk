"""Действия над заявкой: подписание, решение аналитика, справочники."""

from datetime import datetime

from pydantic import Field

from app.schemas.base import CamelModel
from app.schemas.enums import AnalystAction, RejectReason
from app.schemas.application import InfoRequestItem


class SignCodeResponse(CamelModel):
    sent_at: datetime
    expires_at: datetime
    attempts_left: int
    code: str | None = Field(
        default=None, description="Код подписи. Возвращается только в демо-режиме"
    )


class SignRequest(CamelModel):
    code: str = Field(pattern=r"^\d{6}$")


class AnalystDecisionRequest(CamelModel):
    action: AnalystAction
    amount: int | None = Field(default=None, gt=0, description="Сумма для counter_offer")
    comment_for_client: str | None = Field(default=None, description="Обязателен для всех действий, кроме approve")
    reason_code: RejectReason | None = Field(default=None, description="Причина отказа из справочника, для reject")
    info_items: list[InfoRequestItem] | None = Field(default=None, descriprion="Что запросить у клиента, для request_docs")


class DictionaryItem(CamelModel):
    code: str
    label: str


class Dictionaries(CamelModel):
    purpose: list[DictionaryItem]
    collateral_types: list[DictionaryItem]
    reject_reasons: list[DictionaryItem]
    info_items: list[InfoRequestItem] = Field(description="Типовые запросы дополнительной информации")
