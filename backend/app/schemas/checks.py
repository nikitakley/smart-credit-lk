"""Данные проверок по источникам (поле details в карточке аналитика).

Формат details определяется полем source проверки, а при status = unavailable — всегда UnavailableDetails:

    source = bank  → BankDetails          source = nbki → CreditHistoryDetails
    source = egrul → RegistryDetails      source = pb   → RiskDetails

Если данных нет (демо-заявка ещё не обновлялась), details = null.
Модели строгие (лишние поля запрещены): так в ответе API невозможно перепутать один формат с другим.
"""

import logging
from datetime import date
from enum import StrEnum
from typing import Any, Literal

from pydantic import ConfigDict, Field, ValidationError

from app.schemas.base import CamelModel
from app.schemas.enums import CheckSource, CheckStatus

logger = logging.getLogger(__name__)


class DetailsModel(CamelModel):
    model_config = ConfigDict(extra="forbid")


class BankDetails(DetailsModel):
    """Внутренние данные банка: обороты по расчётному счёту."""

    monthly_revenue: int = Field(description="Среднемесячные поступления на счёт, ₽")
    revenue_growth: float = Field(description="Изменение оборотов за 12 месяцев, %")
    history_months: int = Field(description="За сколько месяцев есть обороты, мес.")


class RegistryDetails(DetailsModel):
    """ЕГРЮЛ / ЕГРИП."""

    found: bool = Field(description="false — бизнес не найден в реестре, остальные поля пустые")
    registry: Literal["egrul", "egrip"] | None = None
    ogrn: str | None = None
    status: Literal["active", "liquidating", "liquidated", "reorganizing", "bankrupt"] | None = None
    status_name: str | None = Field(default=None, description="Статус словами, как в реестре")
    status_changed_at: date | None = None
    registered_at: date | None = None
    age_months: int | None = Field(default=None, description="Срок с регистрации, мес.")
    head: str | None = Field(default=None, description="Руководитель; у ИП — null")
    head_position: str | None = None
    okved: str | None = Field(default=None, description="Основной ОКВЭД: код и название")
    address: str | None = None


class CreditHistoryDetails(DetailsModel):
    """Бюро кредитных историй. Суммы — в рублях, просрочки — число случаев за 24 месяца."""

    report_id: str
    history_found: bool = Field(description="false — кредитной истории нет; это результат, а не ошибка")
    bureau_score: int | None = Field(default=None, description="Рейтинг бюро, 300–850")
    history_months: int = Field(default=0, description="Длина кредитной истории, мес.")
    active_loans: int = 0
    total_debt: int = Field(default=0, description="Остаток долга по действующим кредитам, ₽")
    monthly_payments: int = Field(default=0, description="Платежи по действующим кредитам, ₽/мес.")
    current_overdue: int = Field(default=0, description="Текущая просроченная задолженность, ₽")
    overdues_up_to_29: int = 0
    overdues_30_to_89: int = 0
    overdues_90_plus: int = 0
    overdues_24m: int = Field(default=0, alias="overdues24m", description="Всего просрочек за 24 месяца")
    inquiries_last_month: int = Field(default=0, description="Запросов кредитной истории за 30 дней")


class RiskDetails(DetailsModel):
    """ФНС «Прозрачный бизнес»."""

    found: bool = Field(description="false — сведений нет, остальные поля пустые")
    tax_regime: str | None = Field(default=None, description="ОСН, УСН, ПСН, ЕСХН, АУСН")
    employees: int | None = Field(default=None, description="Среднесписочная численность")
    mass_address_companies: int | None = Field(default=None, description="Компаний по адресу, если адрес массовый")
    mass_head_companies: int | None = Field(default=None, description="Компаний у руководителя, если он массовый")
    disqualified_persons: bool = False
    unreliable_info: list[str] = Field(default=[], description="Недостоверные сведения: «адрес», «руководитель», «учредитель»")
    tax_arrears: int = Field(default=0, description="Задолженность по налогам, ₽")
    reporting_overdue: bool = Field(default=False, description="Не сдаёт отчётность более года")
    report_year: int | None = Field(default=None, description="Год последней бухгалтерской отчётности")
    revenue: int | None = Field(default=None, description="Выручка за report_year, ₽")
    net_profit: int | None = Field(default=None, description="Чистая прибыль за report_year, ₽")


class UnavailableReason(StrEnum):
    timeout = "timeout"  # источник не ответил вовремя
    connection_error = "connection_error"  # не удалось подключиться
    server_error = "server_error"  # сбой на стороне источника (5xx, 429)
    request_rejected = "request_rejected"  # источник отклонил запрос (4xx: ключ, формат, согласие)
    invalid_response = "invalid_response"  # ответ в неожиданном формате


UNAVAILABLE_REASON_LABELS = {
    UnavailableReason.timeout: "Источник не ответил вовремя",
    UnavailableReason.connection_error: "Нет связи с источником",
    UnavailableReason.server_error: "Сбой на стороне источника",
    UnavailableReason.request_rejected: "Источник отклонил запрос",
    UnavailableReason.invalid_response: "Источник прислал некорректный ответ",
}


class UnavailableDetails(DetailsModel):
    """Источник не ответил после всех попыток."""

    reason: UnavailableReason
    http_status: int | None = Field(default=None, description="HTTP-код ответа источника, если он был")


CheckDetails = BankDetails | RegistryDetails | CreditHistoryDetails | RiskDetails | UnavailableDetails

DETAILS_BY_SOURCE: dict[CheckSource, type[DetailsModel]] = {
    CheckSource.bank: BankDetails,
    CheckSource.egrul: RegistryDetails,
    CheckSource.nbki: CreditHistoryDetails,
    CheckSource.pb: RiskDetails,
}


def parse_details(source: CheckSource, status: CheckStatus, data: dict[str, Any] | None) -> CheckDetails | None:
    """Прочитать details из базы в модель нужного формата. Нет данных или старый формат — None."""
    if not data:
        return None
    model = UnavailableDetails if status == CheckStatus.unavailable else DETAILS_BY_SOURCE[source]
    try:
        return model.model_validate(data)
    except ValidationError:
        logger.warning("details проверки %s в неизвестном формате — не показываются", source)
        return None
