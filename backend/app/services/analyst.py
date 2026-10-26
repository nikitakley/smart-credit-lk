"""Сервис сотрудника банка: очередь заявок, карточка, решение по спорным случаям."""

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.config import get_settings
from app.db import models
from app.errors import FieldError, conflict, not_found, validation_error
from app.schemas.actions import AnalystDecisionRequest
from app.schemas.auth import User
from app.schemas.enums import (
    Actor,
    AnalystAction,
    ApplicationStatus,
    Collateral,
    DecidedBy,
    DecisionOutcome,
    OfferType,
)
from app.services.common import commit, load_application, now
from app.services.finance import KEY_RATE, annuity_payment
from app.services.state_machine import transition

DECISION_ALLOWED = (ApplicationStatus.manual_review, ApplicationStatus.docs_requested)

ACTION_RESULT = {
    AnalystAction.approve: (DecisionOutcome.approved, ApplicationStatus.approved),
    AnalystAction.counter_offer: (DecisionOutcome.counter_offer, ApplicationStatus.counter_offer),
    AnalystAction.reject: (DecisionOutcome.rejected, ApplicationStatus.rejected),
}


def queue(db: Session, status: ApplicationStatus | None) -> list[models.Application]:
    query = (
        select(models.Application)
        .options(
            joinedload(models.Application.company),
            joinedload(models.Application.product),
            selectinload(models.Application.decisions),
        )
        .where(models.Application.status != ApplicationStatus.draft)
        .order_by(models.Application.created_at.desc())
    )
    if status is not None:
        query = query.where(models.Application.status == status)
    return list(db.scalars(query))


def get(db: Session, application_id: str) -> models.Application:
    app = load_application(db, application_id)
    if app is None or app.status == ApplicationStatus.draft:
        raise not_found("application", "Заявка не найдена")
    return app


def _validate(app: models.Application, req: AnalystDecisionRequest) -> str:
    errors: list[FieldError] = []
    comment = (req.comment_for_client or "").strip()
    if req.action != AnalystAction.approve and not comment:
        errors.append(FieldError(field="commentForClient", code="required", message="Добавьте комментарий для клиента"))
    if req.action == AnalystAction.counter_offer and (req.amount is None or not 0 < req.amount < (app.amount or 0)):
        errors.append(FieldError(field="amount", code="out_of_range",
                                 message="Сумма контрпредложения должна быть меньше запрошенной"))
    if req.action == AnalystAction.reject and req.reason_code is None:
        errors.append(FieldError(field="reasonCode", code="required", message="Выберите причину отказа"))
    if req.action == AnalystAction.request_docs and not req.info_items:
        errors.append(FieldError(field="infoItems", code="required", message="Укажите, что запросить у клиента"))
    if errors:
        raise validation_error(errors)
    return comment


def _rate_breakdown(app: models.Application) -> dict:
    """Ставка — из последнего скоринга; если скоринга не было, базовая ставка продукта."""
    scoring = app.scoring_results[-1] if app.scoring_results else None
    if scoring and scoring.rate_breakdown:
        return scoring.rate_breakdown
    spread = float(app.product.spread)
    return {"key_rate": KEY_RATE, "product_spread": spread, "risk_premium": 0.0, "rate": round(KEY_RATE + spread, 2)}


def _followed_system(app: models.Application, outcome: DecisionOutcome) -> bool | None:
    scoring = app.scoring_results[-1] if app.scoring_results else None
    if scoring is None:
        return None
    recommended = scoring.recommendation.get("outcome")
    # «Ручная проверка» — не решение, а передача специалисту; одобрение в этом случае
    # считаем согласием с финансовой частью рекомендации
    return recommended == outcome or (recommended == DecisionOutcome.manual_review and outcome == DecisionOutcome.approved)


def decide(db: Session, user: User, application_id: str, req: AnalystDecisionRequest) -> models.Application:
    app = get(db, application_id)
    if app.status not in DECISION_ALLOWED:
        raise conflict("decision_not_allowed", "Решение по заявке в этом статусе не принимается")
    comment = _validate(app, req)

    if req.action == AnalystAction.request_docs:
        app.info_requests.append(models.InfoRequest(
            comment=comment, items=[i.model_dump(mode="json") for i in req.info_items or []],
            requested_by=Actor.analyst,
        ))
        transition(app, ApplicationStatus.docs_requested, Actor.analyst, actor_account_id=user.account_id, note=comment)
        commit(db)
        return get(db, application_id)

    outcome, status = ACTION_RESULT[req.action]
    approved_amount = {AnalystAction.approve: app.amount, AnalystAction.counter_offer: req.amount}.get(req.action)
    app.decisions.append(models.Decision(
        outcome=outcome, requested_amount=app.amount or 0, approved_amount=approved_amount,
        decided_by=DecidedBy.analyst, decided_by_account_id=user.account_id,
        comment_for_client=comment or None, reason_code=req.reason_code,
        followed_system=_followed_system(app, outcome),
    ))

    if approved_amount:
        breakdown = _rate_breakdown(app)
        term = app.term_months or app.product.max_term_months
        app.offers.append(models.Offer(
            type=OfferType.approved if outcome == DecisionOutcome.approved else OfferType.counter_offer,
            amount=approved_amount, term_months=term,
            rate=Decimal(str(breakdown["rate"])), rate_breakdown=breakdown,
            monthly_payment=annuity_payment(approved_amount, breakdown["rate"], term),
            collateral_required=Collateral.none,
            requested={"amount": app.amount, "term_months": term,
                       "collateral": (app.collateral or Collateral.none).value},
            valid_until=now() + timedelta(days=get_settings().offer_ttl_days),
        ))

    transition(app, status, Actor.analyst, actor_account_id=user.account_id, note=comment or None)
    commit(db)
    return get(db, application_id)
