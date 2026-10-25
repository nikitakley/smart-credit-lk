"""ORM-модели: таблицы базы данных кредитного конвейера.

Справочники и клиенты:   products, companies, bank_profiles, accounts
Заявка и её жизненный цикл:
    applications       — заявка (параметры, статус, версия для оптимистичной блокировки)
    application_events — история переходов статусов (таймлайн и аудит)
    checks             — результаты проверок по источникам (банк, НБКИ, ЕГРЮЛ, «Прозрачный бизнес»)
    scoring_results    — результаты скоринга (каждый прогон сохраняется)
    decisions          — кредитные решения системы и специалиста
    info_requests      — запросы дополнительной информации и ответы клиента
    offers             — предложения банка
    contracts          — договор: подписание и выдача
    sign_codes         — одноразовые коды подписи (только хеши)
    idempotency_keys   — ключи повторных запросов
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Index, Numeric, Sequence, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.schemas.enums import (
    Actor,
    ApplicationStatus,
    CheckSource,
    CheckStatus,
    Collateral,
    CompanyStatus,
    CompanyType,
    DecidedBy,
    DecisionOutcome,
    OfferType,
    Purpose,
    RejectReason,
    Role,
)
from app.db.base import Base, TimestampMixin, enum_column


# Номера заявок: A-1000, A-1001, ...
# Последовательность гарантирует уникальность даже при одновременном создании заявок несколькими экземплярами API.
application_number_seq = Sequence("application_number_seq", start=1000, metadata=Base.metadata)


# --- [Справочники и клиенты]


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    note: Mapped[str] = mapped_column(String(500))
    min_amount: Mapped[int] = mapped_column(BigInteger)
    max_amount: Mapped[int] = mapped_column(BigInteger)
    max_term_months: Mapped[int]
    spread: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    is_active: Mapped[bool] = mapped_column(default=True)


class Company(TimestampMixin, Base):
    """Компания клиента. Банк знает её заранее: клиент уже обслуживается."""

    __tablename__ = "companies"

    inn: Mapped[str] = mapped_column(String(12), primary_key=True)
    type: Mapped[CompanyType] = mapped_column(enum_column(CompanyType))
    status: Mapped[CompanyStatus] = mapped_column(enum_column(CompanyStatus))
    name: Mapped[str] = mapped_column(String(300))
    full_name: Mapped[str] = mapped_column(String(500))
    ogrn: Mapped[str] = mapped_column(String(15), unique=True)
    kpp: Mapped[str | None] = mapped_column(String(9))
    registered_at: Mapped[date]
    director: Mapped[str] = mapped_column(String(300))
    director_title: Mapped[str] = mapped_column(String(100))
    founders: Mapped[list[Any]] = mapped_column(default=list)
    okved_code: Mapped[str] = mapped_column(String(10))
    okved_title: Mapped[str] = mapped_column(String(500))
    legal_address: Mapped[str] = mapped_column(String(500))
    phone: Mapped[str] = mapped_column(String(30))
    email: Mapped[str] = mapped_column(String(200))
    account: Mapped[str] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(50), default="ФНС")
    fetched_at: Mapped[datetime]

    bank_profile: Mapped["BankProfile | None"] = relationship(back_populates="company")


class BankProfile(TimestampMixin, Base):
    """Внутренние данные банка о клиенте: обороты по расчётному счёту."""

    __tablename__ = "bank_profiles"

    company_inn: Mapped[str] = mapped_column(ForeignKey("companies.inn", ondelete="CASCADE"), primary_key=True)
    monthly_revenue: Mapped[int] = mapped_column(BigInteger, comment="Среднемесячные поступления на счёт, ₽")
    revenue_growth: Mapped[Decimal] = mapped_column(Numeric(6, 2), comment="Рост оборотов за 12 мес., %")
    history_months: Mapped[int] = mapped_column(comment="За сколько месяцев есть обороты в банке")

    company: Mapped[Company] = relationship(back_populates="bank_profile")


class Account(TimestampMixin, Base):
    """Учётная запись пользователя: клиент (сотрудник компании) или аналитик банка."""

    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    role: Mapped[Role] = mapped_column(enum_column(Role))
    name: Mapped[str] = mapped_column(String(300))
    hint: Mapped[str] = mapped_column(String(500), default="")
    company_inn: Mapped[str | None] = mapped_column(ForeignKey("companies.inn"))
    is_active: Mapped[bool] = mapped_column(default=True)

    company: Mapped[Company | None] = relationship()


# --- [Заявка]


class Application(TimestampMixin, Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    company_inn: Mapped[str] = mapped_column(ForeignKey("companies.inn"))
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id"))
    amount: Mapped[int | None] = mapped_column(BigInteger)
    term_months: Mapped[int | None]
    purpose: Mapped[Purpose | None] = mapped_column(enum_column(Purpose))
    collateral: Mapped[Collateral | None] = mapped_column(enum_column(Collateral))
    contact: Mapped[dict[str, Any] | None]
    consents: Mapped[dict[str, Any] | None]
    status: Mapped[ApplicationStatus] = mapped_column(enum_column(ApplicationStatus), default=ApplicationStatus.draft)
    company_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        comment="Реквизиты компании на момент подачи — решение принималось по ним"
    )
    submitted_at: Mapped[datetime | None]
    version: Mapped[int] = mapped_column(default=1, comment="Версия записи для оптимистичной блокировки")

    company: Mapped[Company] = relationship()
    product: Mapped[Product | None] = relationship()
    events: Mapped[list["ApplicationEvent"]] = relationship(
        back_populates="application", order_by="ApplicationEvent.id", cascade="all, delete-orphan"
    )
    checks: Mapped[list["Check"]] = relationship(
        back_populates="application", order_by="Check.id", cascade="all, delete-orphan"
    )
    scoring_results: Mapped[list["ScoringResult"]] = relationship(
        back_populates="application", order_by="ScoringResult.id", cascade="all, delete-orphan"
    )
    decisions: Mapped[list["Decision"]] = relationship(
        back_populates="application", order_by="Decision.id", cascade="all, delete-orphan"
    )
    info_requests: Mapped[list["InfoRequest"]] = relationship(
        back_populates="application", order_by="InfoRequest.id", cascade="all, delete-orphan"
    )
    offers: Mapped[list["Offer"]] = relationship(
        back_populates="application", order_by="Offer.id", cascade="all, delete-orphan"
    )
    contract: Mapped["Contract | None"] = relationship(back_populates="application", cascade="all, delete-orphan")

    # SQLAlchemy сам увеличивает version при каждом UPDATE и добавляет условие
    # WHERE version = <прочитанная>. Если запись успели изменить — ошибка StaleDataError.
    __mapper_args__ = {"version_id_col": version}

    __table_args__ = (
        Index("ix_applications_company_status", "company_inn", "status"),
        Index("ix_applications_status_created", "status", "created_at"),
    )


class ApplicationEvent(Base):
    """Запись истории: какой статус, когда, кто перевёл. Только добавляется, не меняется."""

    __tablename__ = "application_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    status: Mapped[ApplicationStatus] = mapped_column(enum_column(ApplicationStatus))
    actor: Mapped[Actor] = mapped_column(enum_column(Actor))
    actor_account_id: Mapped[str | None] = mapped_column(String(50))
    note: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    application: Mapped[Application] = relationship(back_populates="events")


class Check(Base):
    """Результат проверки по источнику. При повторной обработке заявки обновляется."""

    __tablename__ = "checks"
    __table_args__ = (UniqueConstraint("application_id", "source"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"))
    source: Mapped[CheckSource] = mapped_column(enum_column(CheckSource))
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[CheckStatus] = mapped_column(enum_column(CheckStatus))
    summary: Mapped[str] = mapped_column(String(1000))
    details: Mapped[dict[str, Any]] = mapped_column(default=dict, comment="Сырой ответ источника")
    fetched_at: Mapped[datetime | None]

    application: Mapped[Application] = relationship(back_populates="checks")


class ScoringResult(Base):
    """Результат одного прогона скоринга. Все прогоны хранятся — видно, как менялась оценка."""

    __tablename__ = "scoring_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    score: Mapped[int]
    max_score: Mapped[int] = mapped_column(default=1000)
    min_score: Mapped[int]
    inputs: Mapped[dict[str, Any]] = mapped_column(comment="Входные данные: выручка, нагрузка, просрочки...")
    factors: Mapped[list[Any]] = mapped_column(comment="Факторы с баллами")
    rate_breakdown: Mapped[dict[str, Any] | None]
    recommendation: Mapped[dict[str, Any]] = mapped_column(comment="Рекомендация системы")
    explanation: Mapped[str | None] = mapped_column(String(2000))
    improvements: Mapped[list[Any]] = mapped_column(default=list)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    application: Mapped[Application] = relationship(back_populates="scoring_results")


class Decision(Base):
    """Кредитное решение. Актуально последнее: специалист может принять решение после системы."""

    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    outcome: Mapped[DecisionOutcome] = mapped_column(enum_column(DecisionOutcome))
    requested_amount: Mapped[int] = mapped_column(BigInteger)
    approved_amount: Mapped[int | None] = mapped_column(BigInteger)
    decided_by: Mapped[DecidedBy] = mapped_column(enum_column(DecidedBy))
    decided_by_account_id: Mapped[str | None] = mapped_column(String(50))
    comment_for_client: Mapped[str | None] = mapped_column(String(1000))
    reason_code: Mapped[RejectReason | None] = mapped_column(enum_column(RejectReason))
    followed_system: Mapped[bool | None]
    decided_at: Mapped[datetime] = mapped_column(server_default=func.now())

    application: Mapped[Application] = relationship(back_populates="decisions")


class InfoRequest(Base):
    """Запрос дополнительной информации у клиента и его ответ."""

    __tablename__ = "info_requests"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    comment: Mapped[str] = mapped_column(String(1000))
    items: Mapped[list[Any]] = mapped_column(comment="Что запрошено: код, подпись, тип поля")
    requested_by: Mapped[Actor] = mapped_column(enum_column(Actor))
    answers: Mapped[list[Any] | None]
    requested_at: Mapped[datetime] = mapped_column(server_default=func.now())
    responded_at: Mapped[datetime | None]

    application: Mapped[Application] = relationship(back_populates="info_requests")


class Offer(Base):
    """Предложение банка. Действует последнее неотменённое."""

    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    type: Mapped[OfferType] = mapped_column(enum_column(OfferType))
    amount: Mapped[int] = mapped_column(BigInteger)
    term_months: Mapped[int]
    rate: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    rate_breakdown: Mapped[dict[str, Any]]
    monthly_payment: Mapped[int] = mapped_column(BigInteger)
    collateral_required: Mapped[Collateral] = mapped_column(enum_column(Collateral))
    requested: Mapped[dict[str, Any]] = mapped_column(comment="Что просил клиент — для сравнения в контрпредложении")
    valid_until: Mapped[datetime]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    application: Mapped[Application] = relationship(back_populates="offers")


class Contract(Base):
    """Кредитный договор: подписание и выдача средств."""

    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), unique=True)
    contract_number: Mapped[str] = mapped_column(String(50), unique=True)
    amount: Mapped[int] = mapped_column(BigInteger)
    account: Mapped[str] = mapped_column(String(20), comment="Счёт зачисления")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    code_sent_at: Mapped[datetime | None]
    signed_at: Mapped[datetime | None]
    issued_at: Mapped[datetime | None]

    application: Mapped[Application] = relationship(back_populates="contract")


class SignCode(Base):
    """Одноразовый код подписи. Хранится только SHA-256 хеш кода."""

    __tablename__ = "sign_codes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    attempts_left: Mapped[int]
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class IdempotencyKey(Base):
    """Ключ повторного запроса: повторная отправка с тем же ключом не создаёт дубль."""

    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
