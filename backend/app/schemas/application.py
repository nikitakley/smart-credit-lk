"""Заявка на кредит: входные модели и две проекции - клиентская и банковская (для аналитика)."""

from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.base import CamelModel
from app.schemas.enums import (
    Actor,
    ApplicationStatus,
    CheckSource,
    CheckStatus,
    Collateral,
    DecidedBy,
    DecisionOutcome,
    Impact,
    InfoItemType,
    OfferType,
    Purpose,
    RejectReason,
    Weight,
)
from app.schemas.company import Company, CompanyShort


# --- [Входные данные клиента]


class Contact(CamelModel):
    name: str = Field(min_length=1, examples=["Иванов Иван Иванович"])
    phone: str = Field(pattern=r"^\+?[\d\s()-]{10,}$", examples=["+7 (843) 000-27-14"])
    email: str = Field(pattern=r"^\S+@\S+\.\S+$", examples=["finance@prodmarket.example"])


class Consents(CamelModel):
    bki: bool = Field(description="Согласие на запрос в бюро кредитных историй (БКИ)")
    personal_data: bool = Field(description="Согласие на обработку персональных данных")


class ApplicationCreate(CamelModel):
    """Создание черновика. Поля необязательны - мастер заполняет их по шагам."""

    product_id: str | None = Field(default=None, examples=["working-capital"])
    amount: int | None = Field(default=None, gt=0, examples=[1500000])
    term_months: int | None = Field(default=None, gt=0, le=120, examples=[24])
    purpose: Purpose | None = Field(default=None, examples=[Purpose.working_capital])
    collateral: Collateral | None = Field(default=None, examples=[Collateral.none])
    contact: Contact | None = None


class ApplicationUpdate(ApplicationCreate):
    """Частичное обновление черновика: передаются только изменённые поля."""


class SubmitRequest(CamelModel):
    consents: Consents


class InfoAnswer(CamelModel):
    code: str = Field(examples=["monthly_revenue_confirm"])
    value: str = Field(examples=["900000"])


class InfoResponseRequest(CamelModel):
    answers: list[InfoAnswer] = Field(min_length=1)
    comment: str | None = None


# --- [Части заявки]


class HistoryEvent(CamelModel):
    status: ApplicationStatus
    at: datetime
    actor: Actor
    note: str | None = None


class Check(CamelModel):
    """Результат проверки по источнику. Клиент не видит деталей."""

    source: CheckSource
    title: str = Field(examples=["Бюро кредитных историй"])
    status: CheckStatus
    summary: str = Field(examples=["Просрочек за 24 месяца нет"])
    fetched_at: datetime | None = None


class CheckDetailed(Check):
    details: dict[str, Any] = Field(default_factory=dict, description="Сырые данные источника (для аналитика)")


class Factor(CamelModel):
    """Фактор и его влияние. Клиент не видит баллов."""
    code: str
    label: str
    detail: str
    impact: Impact
    weight: Weight


class ScoredFactor(Factor):
    points: int


class Score(CamelModel):
    value: int
    max: int = 1000
    min_score: int = Field(description="Порог одобрения")


class ScoringInputs(CamelModel):
    monthly_revenue: int
    revenue_growth: float = Field(description="Рост выручки за 12 мес., %")
    loan_payments: int = Field(description="Ежемесячные платежи по текущим кредитам, ₽")
    overdues_24m: int = Field(alias="overdues24m", description="Число просрочек за 24 мес.")
    age_months: int = Field(description="Срок работы бизнеса, мес.")
    dti_now: float = Field(description="Доля платежей в выручке сейчас, %")
    dti_with_requested: float = Field(description="Доля платежей с новым кредитом, %")
    affordable: int = Field(description="Максимальная сумма в пределах лимита нагрузки, ₽")


class RateBreakdown(CamelModel):
    key_rate: float
    product_spread: float
    risk_premium: float
    rate: float


class SystemRecommendation(CamelModel):
    outcome: DecisionOutcome
    amount: int | None = None
    term_months: int | None = None
    rate: float | None = None
    text: str


class Decision(CamelModel):
    outcome: DecisionOutcome
    requested_amount: int
    approved_amount: int | None = None
    decided_by: DecidedBy
    decided_at: datetime
    comment_for_client: str | None = None
    reason_code: RejectReason | None = None
    followed_system: bool | None = Field(default=None, description="Совпадает ли с рекомендацией системы")


class Explanation(CamelModel):
    text: str
    generated_at: datetime
    source: str = Field(default="rules", description="Объяснение строится правилами")


class OfferRequested(CamelModel):
    amount: int
    term_months: int
    collateral: Collateral


class Offer(CamelModel):
    type: OfferType
    amount: int
    term_months: int
    rate: float
    rate_breakdown: RateBreakdown
    monthly_payment: int
    collateral_required: Collateral
    valid_until: datetime
    requested: OfferRequested


class InfoRequestItem(CamelModel):
    code: str = Field(examples=["monthly_revenue_confirm"])
    label: str = Field(examples=["Среднемесячная выручка за последние 6 месяцев, ₽"])
    type: InfoItemType
    required: bool = True


class InfoRequest(CamelModel):
    requested_at: datetime
    comment: str
    items: list[InfoRequestItem]
    responded_at: datetime | None = None


class Signing(CamelModel):
    contract_number: str
    created_at: datetime
    code_sent_at: datetime | None = None
    signed_at: datetime | None = None


class Issuance(CamelModel):
    contract_number: str
    signed_at: datetime
    issued_at: datetime
    amount: int
    account: str


# --- [Проекции заявки]


class ApplicationBase(CamelModel):
    id: str = Field(examples=["A-1024"])
    company: Company
    product_id: str | None = None
    product_name: str | None = None
    amount: int | None = None
    term_months: int | None = None
    purpose: Purpose | None = None
    collateral: Collateral | None = None
    contact: Contact | None = None
    status: ApplicationStatus
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None = None
    history: list[HistoryEvent] = []
    decision: Decision | None = None
    explanation: Explanation | None = None
    improvements: list[str] = []
    offer: Offer | None = None
    info_request: InfoRequest | None = None
    signing: Signing | None = None
    issuance: Issuance | None = None


class ApplicationClient(ApplicationBase):
    """Заявка со стороны клиента: нет внутренних оценок банка."""

    checks: list[Check] = []
    factors: list[Factor] = []


class ApplicationAnalyst(ApplicationBase):
    """Заявка со стороны сотрудника банка: полная информация."""

    checks: list[CheckDetailed] = []
    factors: list[ScoredFactor] = []
    score: Score | None = None
    scoring_inputs: ScoringInputs | None = None
    rate_breakdown: RateBreakdown | None = None
    system_recommendation: SystemRecommendation | None = None


class ApplicationSummary(CamelModel):
    """Строка списка "Мои заявки" (со стороны клиента)."""

    id: str
    product_id: str | None = None
    product_name: str | None = None
    amount: int | None = None
    term_months: int | None = None
    status: ApplicationStatus
    created_at: datetime
    updated_at: datetime


class AnalystQueueItem(CamelModel):
    """Строка очереди аналитика."""

    id: str
    company: CompanyShort
    product_id: str | None = None
    product_name: str | None = None
    amount: int | None = None
    term_months: int | None = None
    status: ApplicationStatus
    created_at: datetime
    submitted_at: datetime | None = None
    decision_outcome: DecisionOutcome | None = None
    decided_by: DecidedBy | None = None
    followed_system: bool | None = None
