"""Загрузка начальных и демо-данных из data/seed в базу.

Запуск из папки backend (база должна быть поднята, миграции применены):
    uv run python -m app.db.seed            справочники + демо-заявки, если заявок ещё нет
    uv run python -m app.db.seed --reset    справочники + пересоздать демо-заявки с нуля

Справочники (продукты, компании, учётки) загружаются идемпотентно: повторный запуск
обновляет записи, а не создаёт дубли. Демо-заявки не трогаются, если в базе уже есть заявки,
чтобы перезапуск контейнера не стёр данные, созданные во время проверки.
"""

import argparse
import json
import logging
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, TypeVar

from pydantic import ConfigDict, Field
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.schemas.application import Contact, InfoRequestItem, ScoredFactor, ScoringInputs
from app.schemas.base import CamelModel
from app.schemas.company import Founder
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
from app.services.finance import KEY_RATE, annuity_payment
from app.services.mappers import company_to_schema
from app.services.requisites import is_valid_account, is_valid_inn, is_valid_ogrn
from app.db import models
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

BANK_BIK = "044525593"  # БИК банка — для проверки контрольного ключа расчётных счетов

CHECK_TITLES = {
    CheckSource.bank: "Обороты по счёту в банке",
    CheckSource.egrul: "ЕГРЮЛ / ЕГРИП",
    CheckSource.pb: "ФНС «Прозрачный бизнес»",
    CheckSource.nbki: "Бюро кредитных историй",
}


# --- [Формат файлов data/seed] (строгая проверка)


class SeedModel(CamelModel):
    model_config = ConfigDict(extra="forbid")


class SeedProduct(SeedModel):
    id: str
    name: str
    note: str
    min_amount: int
    max_amount: int
    max_term_months: int
    spread: Decimal


class SeedOkved(SeedModel):
    code: str
    title: str


class SeedBankProfile(SeedModel):
    monthly_revenue: int
    revenue_growth: Decimal
    history_months: int


class SeedCompany(SeedModel):
    inn: str
    type: CompanyType
    status: CompanyStatus
    name: str
    full_name: str
    ogrn: str
    kpp: str | None
    registered_at: date
    director: str
    director_title: str
    founders: list[Founder] = []
    okved: SeedOkved
    legal_address: str
    phone: str
    email: str
    account: str
    bank_profile: SeedBankProfile


class SeedAccount(SeedModel):
    id: str
    role: Role
    company_inn: str | None
    name: str
    hint: str = ""


class SeedEvent(SeedModel):
    status: ApplicationStatus
    actor: Actor
    after_seconds: int = 0
    note: str | None = None


class SeedCheck(SeedModel):
    source: CheckSource
    status: CheckStatus
    summary: str
    details: dict[str, Any] = {}


class SeedRecommendation(SeedModel):
    outcome: DecisionOutcome
    amount: int | None = None
    term_months: int | None = None
    text: str


class SeedScoring(SeedModel):
    score: int
    min_score: int
    inputs: ScoringInputs
    factors: list[ScoredFactor]
    risk_premium: float | None
    recommendation: SeedRecommendation
    explanation: str | None = None
    improvements: list[str] = []


class SeedDecision(SeedModel):
    outcome: DecisionOutcome
    approved_amount: int | None = None
    decided_by: DecidedBy
    reason_code: RejectReason | None = None
    comment_for_client: str | None = None
    followed_system: bool | None = None
    after_seconds: int = 0


class SeedOffer(SeedModel):
    type: OfferType
    amount: int
    term_months: int
    risk_premium: float
    valid_days: int


class SeedInfoRequest(SeedModel):
    requested_by: Actor
    after_seconds: int = 0
    comment: str
    items: list[InfoRequestItem]


class SeedApplication(SeedModel):
    id: str = Field(pattern=r"^A-\d+$")
    company_inn: str
    product_id: str
    amount: int
    term_months: int
    purpose: Purpose
    collateral: Collateral
    status: ApplicationStatus
    created_minutes_ago: int
    events: list[SeedEvent] = []
    checks: list[SeedCheck] = []
    scoring: SeedScoring | None = None
    decision: SeedDecision | None = None
    offer: SeedOffer | None = None
    info_request: SeedInfoRequest | None = None


# --- [Чтение файлов]

T = TypeVar("T", bound=SeedModel)


def _read(name: str, model: type[T], seed_dir: Path) -> list[T]:
    path = seed_dir / name
    data = json.loads(path.read_text(encoding="utf-8"))
    return [model.model_validate(item) for item in data]


# --- [Справочники]


def seed_reference_data(session: Session, seed_dir: Path) -> None:
    """Продукты, компании с банковскими профилями, учётки. Повторный запуск обновляет записи."""
    now = datetime.now(UTC)

    for p in _read("products.json", SeedProduct, seed_dir):
        session.merge(models.Product(**p.model_dump()))

    for c in _read("companies.json", SeedCompany, seed_dir):
        if not (is_valid_inn(c.inn) and is_valid_ogrn(c.ogrn) and is_valid_account(c.account, BANK_BIK)):
            raise ValueError(f"Неверные реквизиты компании {c.name}: проверьте контрольные суммы")
        session.merge(models.Company(
            inn=c.inn, type=c.type, status=c.status, name=c.name, full_name=c.full_name, ogrn=c.ogrn,
            kpp=c.kpp, registered_at=c.registered_at, director=c.director, director_title=c.director_title,
            founders=[f.model_dump() for f in c.founders],
            okved_code=c.okved.code, okved_title=c.okved.title,
            legal_address=c.legal_address, phone=c.phone, email=c.email, account=c.account,
            source="ФНС", fetched_at=now,
        ))
        session.merge(models.BankProfile(company_inn=c.inn, **c.bank_profile.model_dump()))

    session.flush()  # компании должны оказаться в базе раньше учёток, которые на них ссылаются
    for a in _read("accounts.json", SeedAccount, seed_dir):
        session.merge(models.Account(**a.model_dump()))
    session.flush()


# --- [Демо-заявки]


def _rate_breakdown(product: models.Product, risk_premium: float) -> dict[str, float]:
    spread = float(product.spread)
    return {
        "key_rate": KEY_RATE,
        "product_spread": spread,
        "risk_premium": risk_premium,
        "rate": round(KEY_RATE + spread + risk_premium, 2),
    }


def _build_application(seed: SeedApplication, session: Session, now: datetime) -> models.Application:
    company = session.get(models.Company, seed.company_inn)
    product = session.get(models.Product, seed.product_id)
    if company is None or product is None:
        raise ValueError(f"Заявка {seed.id}: неизвестная компания или продукт")

    client_account = session.scalar(select(models.Account).where(models.Account.company_inn == company.inn))
    created = now - timedelta(minutes=seed.created_minutes_ago)
    is_draft = seed.status == ApplicationStatus.draft
    last_event = created + timedelta(seconds=max((e.after_seconds for e in seed.events), default=0))

    app = models.Application(
        id=seed.id,
        company_inn=company.inn,
        product_id=product.id,
        amount=seed.amount,
        term_months=seed.term_months,
        purpose=seed.purpose,
        collateral=seed.collateral,
        contact=Contact(name=company.director, phone=company.phone, email=company.email).model_dump(),
        consents=None if is_draft else {"bki": True, "personal_data": True},
        status=seed.status,
        company_snapshot=None if is_draft else company_to_schema(company).model_dump(mode="json"),
        submitted_at=None if is_draft else created,
        created_at=created,
        updated_at=last_event,
    )

    for e in seed.events:
        app.events.append(models.ApplicationEvent(
            status=e.status, actor=e.actor, note=e.note,
            actor_account_id=client_account.id if e.actor == Actor.client and client_account else None,
            created_at=created + timedelta(seconds=e.after_seconds),
        ))

    for c in seed.checks:
        app.checks.append(models.Check(
            source=c.source, title=CHECK_TITLES[c.source], status=c.status, summary=c.summary,
            details=c.details, fetched_at=created + timedelta(seconds=10),
        ))

    if s := seed.scoring:
        rate_breakdown = _rate_breakdown(product, s.risk_premium) if s.risk_premium is not None else None
        recommendation = s.recommendation.model_dump()
        recommendation["rate"] = rate_breakdown["rate"] if rate_breakdown and s.recommendation.amount else None
        app.scoring_results.append(models.ScoringResult(
            score=s.score, min_score=s.min_score,
            inputs=s.inputs.model_dump(), factors=[f.model_dump(mode="json") for f in s.factors],
            rate_breakdown=rate_breakdown, recommendation=recommendation,
            explanation=s.explanation, improvements=s.improvements,
            created_at=created + timedelta(seconds=20),
        ))

    if d := seed.decision:
        app.decisions.append(models.Decision(
            outcome=d.outcome, requested_amount=seed.amount, approved_amount=d.approved_amount,
            decided_by=d.decided_by, comment_for_client=d.comment_for_client, reason_code=d.reason_code,
            followed_system=d.followed_system, decided_at=created + timedelta(seconds=d.after_seconds),
        ))

    if o := seed.offer:
        breakdown = _rate_breakdown(product, o.risk_premium)
        app.offers.append(models.Offer(
            type=o.type, amount=o.amount, term_months=o.term_months, rate=Decimal(str(breakdown["rate"])),
            rate_breakdown=breakdown, monthly_payment=annuity_payment(o.amount, breakdown["rate"], o.term_months),
            collateral_required=Collateral.none,
            requested={"amount": seed.amount, "term_months": seed.term_months, "collateral": seed.collateral.value},
            # срок считаем от текущего момента, чтобы демо-оффер всегда был действующим
            valid_until=now + timedelta(days=o.valid_days),
            created_at=last_event,
        ))

    if r := seed.info_request:
        app.info_requests.append(models.InfoRequest(
            comment=r.comment, items=[i.model_dump(mode="json") for i in r.items], requested_by=r.requested_by,
            requested_at=created + timedelta(seconds=r.after_seconds),
        ))

    return app


def sync_application_sequence(session: Session) -> None:
    """Сдвинуть последовательность номеров за максимальный существующий номер.
    Иначе новая заявка однажды получила бы номер уже существующей демо-заявки."""
    session.execute(text(
        "SELECT setval('application_number_seq', "
        "(SELECT COALESCE(MAX(CAST(SUBSTRING(id FROM 3) AS INTEGER)), 999) FROM applications))"
    ))


def reset_demo_applications(session: Session, seed_dir: Path) -> int:
    """Удалить все заявки и создать демо-заявки заново. Возвращает число созданных заявок."""
    session.execute(delete(models.IdempotencyKey))
    session.execute(delete(models.SignCode))
    # Дочерние записи (события, проверки, офферы...) удалит сама БД: ON DELETE CASCADE
    session.execute(delete(models.Application))

    now = datetime.now(UTC)
    seeds = _read("demo_applications.json", SeedApplication, seed_dir)
    for seed in seeds:
        session.add(_build_application(seed, session, now))
    session.flush()
    sync_application_sequence(session)
    return len(seeds)


def run(reset: bool = False) -> None:
    seed_dir = get_settings().seed_dir
    with SessionLocal() as session:
        seed_reference_data(session, seed_dir)
        has_applications = session.scalar(select(func.count()).select_from(models.Application)) > 0
        if reset or not has_applications:
            created = reset_demo_applications(session, seed_dir)
            logger.info("Демо-заявки созданы: %d", created)
        else:
            logger.info("Заявки уже есть — демо-данные не пересоздаются (для пересоздания: --reset)")
        session.commit()
    logger.info("Справочники загружены из %s", seed_dir)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Загрузка начальных и демо-данных")
    parser.add_argument("--reset", action="store_true", help="пересоздать демо-заявки (все заявки будут удалены)")
    run(reset=parser.parse_args().reset)
