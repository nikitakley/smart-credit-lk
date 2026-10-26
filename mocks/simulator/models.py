"""Форматы ответов внешних источников.

Это «чужие» форматы: поля в snake_case и со своей структурой — так, как их отдавал бы внешний сервис.
Бэкенд банка не использует их напрямую, а переводит в свои модели (см. backend/app/integrations).
Те же модели проверяют файлы data/*.json при запуске: опечатка в данных — ошибка старта, а не «тихий» сбой.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

INN_PATTERN = r"^\d{10}(\d{2})?$"


class ExternalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- [ЕГРЮЛ / ЕГРИП]


class EgrStatus(ExternalModel):
    code: Literal["active", "liquidating", "liquidated", "reorganizing", "bankrupt"]
    name: str
    changed_at: date | None = Field(default=None, description="Дата изменения статуса")


class EgrAddress(ExternalModel):
    text: str
    region: str


class EgrHead(ExternalModel):
    full_name: str
    position: str
    inn: str = Field(pattern=INN_PATTERN)


class EgrFounder(ExternalModel):
    full_name: str
    share_percent: float = Field(gt=0, le=100)


class Okved(ExternalModel):
    code: str
    title: str


class EgrRecord(ExternalModel):
    registry: Literal["EGRUL", "EGRIP"]
    inn: str = Field(pattern=INN_PATTERN)
    ogrn: str
    kpp: str | None
    full_name: str
    short_name: str
    registration_date: date
    status: EgrStatus
    address: EgrAddress
    head: EgrHead | None = Field(description="Руководитель юрлица; для ИП — null")
    founders: list[EgrFounder] = []
    okved_main: Okved
    okved_additional: list[Okved] = []
    authorized_capital: int | None = Field(description="Уставный капитал, ₽; для ИП — null")
    registering_authority: str


class EgrExtract(EgrRecord):
    """Выписка из реестра."""

    request_id: str
    extract_date: date


# --- [НБКИ]


class Loan(ExternalModel):
    type: Literal["loan", "credit_line", "overdraft", "credit_card", "leasing"]
    creditor_type: Literal["bank", "leasing_company", "mfo"]
    opened_at: date
    closed_at: date | None = None
    limit: int
    balance: int = Field(description="Остаток долга, ₽")
    monthly_payment: int = Field(description="Ежемесячный платёж, ₽")
    status: Literal["active", "closed"]
    current_overdue: int = Field(default=0, description="Текущая просроченная задолженность, ₽")


class PaymentDiscipline(ExternalModel):
    """Число просрочек за 24 месяца по длительности."""

    overdue_1_29: int = 0
    overdue_30_59: int = 0
    overdue_60_89: int = 0
    overdue_90_plus: int = 0


class NbkiRecord(ExternalModel):
    inn: str = Field(pattern=INN_PATTERN)
    score: int | None = Field(ge=300, le=850, description="Кредитный рейтинг бюро")
    history_length_months: int
    loans: list[Loan]
    payment_discipline_24m: PaymentDiscipline
    inquiries_30d: int = Field(description="Запросов кредитной истории за 30 дней")


class Consent(ExternalModel):
    given: bool
    given_at: datetime
    purpose: str = Field(examples=["loan_application"])


class CreditReportRequest(ExternalModel):
    inn: str = Field(pattern=INN_PATTERN, examples=["1655482318"])
    subject_type: Literal["legal_entity", "individual_entrepreneur"]
    consent: Consent


class CreditReport(ExternalModel):
    report_id: str
    generated_at: datetime
    inn: str
    history_found: bool = Field(description="false — кредитной истории в бюро нет; это результат, а не ошибка")
    score: int | None = None
    history_length_months: int = 0
    loans: list[Loan] = []
    payment_discipline_24m: PaymentDiscipline = PaymentDiscipline()
    inquiries_30d: int = 0


# --- [ФНС «Прозрачный бизнес»]


class Marker(ExternalModel):
    flag: bool
    companies_count: int = Field(description="Сколько организаций связано с адресом или руководителем")


class TaxArrears(ExternalModel):
    has_arrears: bool
    amount: int = 0


class FinancialYear(ExternalModel):
    year: int
    revenue: int
    net_profit: int


class PbRecord(ExternalModel):
    inn: str = Field(pattern=INN_PATTERN)
    tax_regime: Literal["ОСН", "УСН", "ПСН", "ЕСХН", "АУСН"]
    employees_avg: int | None
    mass_address: Marker
    mass_head: Marker
    disqualified_persons: bool = Field(description="Есть дисквалифицированные лица в органах управления")
    unreliable_info: list[Literal["address", "head", "founder"]] = Field(
        description="Сведения, отмеченные в реестре как недостоверные"
    )
    tax_arrears: TaxArrears
    reporting_overdue: bool = Field(description="Не представляет налоговую отчётность более года")
    financials: list[FinancialYear] = Field(description="Бухгалтерская отчётность; у ИП её нет")


class PbProfile(PbRecord):
    request_id: str
    checked_at: datetime


# --- [Служебное]


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
