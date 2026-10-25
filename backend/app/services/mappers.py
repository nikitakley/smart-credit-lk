"""Преобразование ORM-моделей (как данные хранятся) в схемы API (как их видит клиент)."""

from app.schemas.product import Product
from app.schemas.company import Company, CompanyShort, Founder, Okved
from app.schemas.application import (
    AnalystQueueItem,
    ApplicationAnalyst,
    ApplicationClient,
    ApplicationSummary,
    CheckDetailed,
    Contact,
    Decision,
    Explanation,
    HistoryEvent,
    InfoRequest,
    Issuance,
    Offer,
    OfferRequested,
    RateBreakdown,
    Score,
    ScoredFactor,
    ScoringInputs,
    Signing,
    SystemRecommendation,
)
from app.services.finance import KEY_RATE
from app.db import models

# --- [Справочники]


def product_to_schema(product: models.Product) -> Product:
    spread = float(product.spread)
    return Product(
        id=product.id,
        name=product.name,
        note=product.note,
        min_amount=product.min_amount,
        max_amount=product.max_amount,
        max_term_months=product.max_term_months,
        spread=spread,
        rate_from=round(KEY_RATE + spread, 2),  # в базе не хранится
    )


def company_to_schema(company: models.Company) -> Company:
    return Company(
        inn=company.inn,
        type=company.type,
        status=company.status,
        name=company.name,
        full_name=company.full_name,
        ogrn=company.ogrn,
        kpp=company.kpp,
        registered_at=company.registered_at,
        director=company.director,
        director_title=company.director_title,
        founders=[Founder.model_validate(f) for f in company.founders],
        okved=Okved(code=company.okved_code, title=company.okved_title),
        legal_address=company.legal_address,
        phone=company.phone,
        email=company.email,
        account=company.account,
        source=company.source,
        fetched_at=company.fetched_at,
    )

# --- [Части заявки]


def _latest(items: list):
    """Актуальная запись — последняя добавленная (списки упорядочены по id)."""
    return items[-1] if items else None


def _decision(decision: models.Decision | None) -> Decision | None:
    if decision is None:
        return None
    return Decision(
        outcome=decision.outcome,
        requested_amount=decision.requested_amount,
        approved_amount=decision.approved_amount,
        decided_by=decision.decided_by,
        decided_at=decision.decided_at,
        comment_for_client=decision.comment_for_client,
        reason_code=decision.reason_code,
        followed_system=decision.followed_system,
    )


def _offer(offer: models.Offer | None) -> Offer | None:
    if offer is None:
        return None
    return Offer(
        type=offer.type,
        amount=offer.amount,
        term_months=offer.term_months,
        rate=float(offer.rate),
        rate_breakdown=RateBreakdown.model_validate(offer.rate_breakdown),
        monthly_payment=offer.monthly_payment,
        collateral_required=offer.collateral_required,
        valid_until=offer.valid_until,
        requested=OfferRequested.model_validate(offer.requested),
    )


def _info_request(request: models.InfoRequest | None) -> InfoRequest | None:
    if request is None:
        return None
    return InfoRequest(
        requested_at=request.requested_at,
        comment=request.comment,
        items=request.items,
        responded_at=request.responded_at,
    )


def _signing(contract: models.Contract | None) -> Signing | None:
    if contract is None:
        return None
    return Signing(
        contract_number=contract.contract_number,
        created_at=contract.created_at,
        code_sent_at=contract.code_sent_at,
        signed_at=contract.signed_at,
    )


def _issuance(contract: models.Contract | None) -> Issuance | None:
    if contract is None or contract.issued_at is None or contract.signed_at is None:
        return None
    return Issuance(
        contract_number=contract.contract_number,
        signed_at=contract.signed_at,
        issued_at=contract.issued_at,
        amount=contract.amount,
        account=contract.account,
    )


# --- [Проекции заявки]


def application_to_analyst(app: models.Application) -> ApplicationAnalyst:
    """Полная проекция — для сотрудника банка. Клиентская строится из неё (см. ниже)."""
    scoring = _latest(app.scoring_results)
    # Реквизиты — на момент подачи; у черновика снимка ещё нет, берём текущие
    company = Company.model_validate(app.company_snapshot) if app.company_snapshot else company_to_schema(app.company)

    return ApplicationAnalyst(
        id=app.id,
        company=company,
        product_id=app.product_id,
        product_name=app.product.name if app.product else None,
        amount=app.amount,
        term_months=app.term_months,
        purpose=app.purpose,
        collateral=app.collateral,
        contact=Contact.model_validate(app.contact) if app.contact else None,
        status=app.status,
        created_at=app.created_at,
        updated_at=app.updated_at,
        submitted_at=app.submitted_at,
        history=[
            HistoryEvent(status=e.status, at=e.created_at, actor=e.actor, note=e.note) for e in app.events
        ],
        checks=[
            CheckDetailed(
                source=c.source, title=c.title, status=c.status, summary=c.summary,
                fetched_at=c.fetched_at, details=c.details,
            )
            for c in app.checks
        ],
        factors=[ScoredFactor.model_validate(f) for f in scoring.factors] if scoring else [],
        score=Score(value=scoring.score, max=scoring.max_score, min_score=scoring.min_score) if scoring else None,
        scoring_inputs=ScoringInputs.model_validate(scoring.inputs) if scoring else None,
        rate_breakdown=(
            RateBreakdown.model_validate(scoring.rate_breakdown) if scoring and scoring.rate_breakdown else None
        ),
        system_recommendation=SystemRecommendation.model_validate(scoring.recommendation) if scoring else None,
        explanation=(
            Explanation(text=scoring.explanation, generated_at=scoring.created_at)
            if scoring and scoring.explanation
            else None
        ),
        improvements=scoring.improvements if scoring else [],
        decision=_decision(_latest(app.decisions)),
        offer=_offer(_latest(app.offers)),
        info_request=_info_request(_latest(app.info_requests)),
        signing=_signing(app.contract),
        issuance=_issuance(app.contract),
    )


def application_to_client(app: models.Application) -> ApplicationClient:
    """Клиентская проекция: поля, которых нет в ApplicationClient (score, details, points...), отбрасываются."""
    return ApplicationClient.model_validate(application_to_analyst(app).model_dump())


def application_to_summary(app: models.Application) -> ApplicationSummary:
    return ApplicationSummary(
        id=app.id,
        product_id=app.product_id,
        product_name=app.product.name if app.product else None,
        amount=app.amount,
        term_months=app.term_months,
        status=app.status,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


def application_to_queue_item(app: models.Application) -> AnalystQueueItem:
    decision = _latest(app.decisions)
    return AnalystQueueItem(
        id=app.id,
        company=CompanyShort(inn=app.company.inn, name=app.company.name, type=app.company.type),
        product_id=app.product_id,
        product_name=app.product.name if app.product else None,
        amount=app.amount,
        term_months=app.term_months,
        status=app.status,
        created_at=app.created_at,
        submitted_at=app.submitted_at,
        decision_outcome=decision.outcome if decision else None,
        decided_by=decision.decided_by if decision else None,
        followed_system=decision.followed_system if decision else None,
    )
