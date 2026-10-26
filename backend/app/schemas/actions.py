"""Действия над заявкой: подписание, решение аналитика, справочники."""

from datetime import datetime

from pydantic import Field

from app.schemas.application import InfoRequestItem
from app.schemas.base import CamelModel
from app.schemas.enums import AnalystAction, RejectReason


class SignCodeResponse(CamelModel):
    sent_at: datetime
    expires_at: datetime
    attempts_left: int
    code: str | None = Field(
        default=None,
        description="Код подписи. Возвращается только в демо-режиме (DEMO_SHOW_SIGN_CODE=true)",
    )


class SignRequest(CamelModel):
    code: str = Field(pattern=r"^\d{6}$", examples=["123456"])


class AnalystDecisionRequest(CamelModel):
    action: AnalystAction
    amount: int | None = Field(default=None, gt=0, description="Сумма для counter_offer", examples=[3000000])
    comment_for_client: str | None = Field(
        default=None, description="Обязателен для всех действий, кроме approve",
        examples=["Снизили сумму из-за признаков риска"],
    )
    reason_code: RejectReason | None = Field(default=None, description="Причина отказа, для reject")
    info_items: list[InfoRequestItem] | None = Field(default=None, description="Что запросить у клиента, для request_docs")


class DictionaryItem(CamelModel):
    code: str
    label: str


class Dictionaries(CamelModel):
    purposes: list[DictionaryItem]
    collateral_types: list[DictionaryItem]
    reject_reasons: list[DictionaryItem]
    unavailable_reasons: list[DictionaryItem] = Field(description="Почему источник не ответил (details.reason)")
    info_items: list[InfoRequestItem] = Field(description="Типовые запросы дополнительной информации")
