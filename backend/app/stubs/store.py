"""ВРЕМЕННОЕ хранилище в памяти для заглушек этапа 1.

Дает фронтенду рабочие ответы и переходы статусов по всем эндпоинтам контракта.
Данные живут до перезапуска сервера. Конвейер обработки здесь не работает:
отправленная заявка остаётся в статусе submitted (конвейер — этап 4).
На этапе 2 модуль заменяется сервисами поверх PostgreSQL.
"""

import hashlib
import secrets
from datetime import datetime, timedelta

from app.config import get_settings
from app.errors import ApiError, FieldError, conflict, not_found, validation_error
from app.schemas.actions import AnalystDecisionRequest, SignCodeResponse
from app.schemas.application import (
    ApplicationAnalyst,
    ApplicationClient,
    ApplicationCreate,
    ApplicationSummary,
    AnalystQueueItem,
    Decision,
    HistoryEvent,
    InfoRequest,
    InfoResponseRequest,
    Issuance,
    Offer,
    OfferRequested,
    RateBreakdown,
    Signing,
    SubmitRequest,
)
from app.schemas.auth import User
from app.schemas.company import CompanyShort
from app.schemas.enums import (
    Actor,
    AnalystAction,
    ApplicationStatus as S,
    Collateral,
    DecidedBy,
    DecisionOutcome,
    OfferType,
    TERMINAL_STATUSES,
)
from app.services.finance import KEY_RATE, annuity_payment
from app.stubs.data import MSK, PRODUCTS_BY_ID, build_applications

REJECT_REASONS = {
    "debt_load": "Высокая долговая нагрузка",
    "credit_history": "Негативная кредитная история",
    "company_inactive": "Компания не действует",
    "insufficient_data": "Недостаточно данных для оценки",
    "risk_signals": "Признаки повышенного риска",
    "other": "Другая причина",
}


class _State:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.apps: dict[str, ApplicationAnalyst] = build_applications()
        self.next_number = 1027
        self.idempotency: dict[str, str] = {}
        # application_id -> (hash кода, истекает, осталось попыток)
        self.sign_codes: dict[str, tuple[str, datetime, int]] = {}


state = _State()


def _now() -> datetime:
    return datetime.now(MSK).replace(microsecond=0)


def _hash(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def to_client(app: ApplicationAnalyst) -> ApplicationClient:
    # Лишние поля (score, scoringInputs, details, points...) отбрасываются моделью клиента
    return ApplicationClient.model_validate(app.model_dump())


def _move(app: ApplicationAnalyst, status: S, actor: Actor, note: str | None = None) -> None:
    now = _now()
    app.status = status
    app.updated_at = now
    app.history.append(HistoryEvent(status=status, at=now, actor=actor, note=note))


# --- [Клиент]


def _get_own(user: User, app_id: str) -> ApplicationAnalyst:
    app = state.apps.get(app_id)
    # Чужую заявку не показываем — отвечаем так же, как на несуществующую
    if app is None or app.company.inn != user.inn:
        raise not_found("application", "Заявка не найдена")
    return app


def current_application_id(inn: str) -> str | None:
    own = [a for a in state.apps.values() if a.company.inn == inn and a.status not in TERMINAL_STATUSES]
    own.sort(key=lambda a: a.updated_at, reverse=True)
    return own[0].id if own else None


def list_own(user: User) -> list[ApplicationSummary]:
    own = [a for a in state.apps.values() if a.company.inn == user.inn]
    own.sort(key=lambda a: a.created_at, reverse=True)
    return [ApplicationSummary.model_validate(a.model_dump()) for a in own]


def get_own(user: User, app_id: str) -> ApplicationClient:
    return to_client(_get_own(user, app_id))


def _validate_product_fields(data: ApplicationCreate) -> None:
    errors: list[FieldError] = []
    if data.product_id is not None and data.product_id not in PRODUCTS_BY_ID:
        errors.append(FieldError(field="productId", code="unknown_product", message="Такого продукта нет"))
    if errors:
        raise validation_error(errors)


def create_draft(user: User, data: ApplicationCreate, company) -> ApplicationClient:
    _validate_product_fields(data)
    now = _now()
    app_id = f"A-{state.next_number}"
    state.next_number += 1
    product = PRODUCTS_BY_ID.get(data.product_id) if data.product_id else None
    app = ApplicationAnalyst(
        id=app_id, company=company, product_id=data.product_id, product_name=product.name if product else None,
        amount=data.amount, term_months=data.term_months, purpose=data.purpose, collateral=data.collateral,
        contact=data.contact, status=S.draft, created_at=now, updated_at=now,
    )
    state.apps[app_id] = app
    return to_client(app)


def update_draft(user: User, app_id: str, data: ApplicationCreate) -> ApplicationClient:
    app = _get_own(user, app_id)
    if app.status != S.draft:
        raise conflict("not_draft", "Изменять можно только черновик")
    _validate_product_fields(data)
    changes = data.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(app, key, getattr(data, key))
    if "product_id" in changes:
        product = PRODUCTS_BY_ID.get(app.product_id) if app.product_id else None
        app.product_name = product.name if product else None
    app.updated_at = _now()
    return to_client(app)


def submit(user: User, app_id: str, data: SubmitRequest, idempotency_key: str | None) -> ApplicationClient:
    if idempotency_key and idempotency_key in state.idempotency:
        return get_own(user, state.idempotency[idempotency_key])

    app = _get_own(user, app_id)
    if app.status != S.draft:
        raise conflict("not_draft", "Заявка уже отправлена")

    errors: list[FieldError] = []
    for field, label in [("product_id", "productId"), ("amount", "amount"), ("term_months", "termMonths"),
                         ("purpose", "purpose"), ("contact", "contact")]:
        if getattr(app, field) is None:
            errors.append(FieldError(field=label, code="required", message="Обязательное поле"))
    product = PRODUCTS_BY_ID.get(app.product_id) if app.product_id else None
    if product and app.amount is not None and not (product.min_amount <= app.amount <= product.max_amount):
        errors.append(FieldError(field="amount", code="out_of_range",
                                 message=f"Сумма должна быть от {product.min_amount} до {product.max_amount} ₽"))
    if product and app.term_months is not None and app.term_months > product.max_term_months:
        errors.append(FieldError(field="termMonths", code="out_of_range",
                                 message=f"Срок не больше {product.max_term_months} мес."))
    if not data.consents.bki:
        errors.append(FieldError(field="consents.bki", code="required", message="Нужно согласие на запрос в БКИ"))
    if not data.consents.personal_data:
        errors.append(FieldError(field="consents.personalData", code="required",
                                 message="Нужно согласие на обработку персональных данных"))
    if errors:
        raise validation_error(errors)

    if app.collateral is None:
        app.collateral = Collateral.none
    app.submitted_at = _now()
    _move(app, S.submitted, Actor.client, "Заявка отправлена в банк")
    if idempotency_key:
        state.idempotency[idempotency_key] = app.id
    return to_client(app)


def respond_info(user: User, app_id: str, data: InfoResponseRequest) -> ApplicationClient:
    app = _get_own(user, app_id)
    if app.status != S.docs_requested or app.info_request is None:
        raise conflict("no_info_request", "Банк не запрашивал дополнительную информацию")
    given = {a.code for a in data.answers if a.value.strip()}
    missing = [i for i in app.info_request.items if i.required and i.code not in given]
    if missing:
        raise validation_error([FieldError(field=f"answers.{i.code}", code="required", message=i.label) for i in missing])
    app.info_request.responded_at = _now()
    _move(app, S.validation, Actor.client, "Клиент предоставил дополнительную информацию")
    return to_client(app)


def _check_offer(app: ApplicationAnalyst) -> Offer:
    if app.status not in (S.approved, S.counter_offer) or app.offer is None:
        raise conflict("no_offer", "Нет действующего предложения банка")
    if app.offer.valid_until < _now():
        raise conflict("offer_expired", "Срок действия предложения истёк")
    return app.offer


def accept_offer(user: User, app_id: str) -> ApplicationClient:
    app = _get_own(user, app_id)
    _check_offer(app)
    number = app.id.split("-")[-1]
    app.signing = Signing(contract_number=f"КД-{number}/{_now().year}", created_at=_now())
    _move(app, S.signing, Actor.client, f"Предложение принято, сформирован договор {app.signing.contract_number}")
    return to_client(app)


def decline_offer(user: User, app_id: str) -> ApplicationClient:
    app = _get_own(user, app_id)
    _check_offer(app)
    _move(app, S.declined_by_client, Actor.client, "Клиент отказался от предложения")
    return to_client(app)


def request_sign_code(user: User, app_id: str) -> SignCodeResponse:
    settings = get_settings()
    app = _get_own(user, app_id)
    if app.status != S.signing or app.signing is None:
        raise conflict("not_signing", "Договор сейчас не на подписании")
    code = f"{secrets.randbelow(1_000_000):06d}"
    now = _now()
    expires = now + timedelta(seconds=settings.sign_code_ttl_seconds)
    state.sign_codes[app.id] = (_hash(code), expires, settings.sign_code_max_attempts)
    app.signing.code_sent_at = now
    return SignCodeResponse(sent_at=now, expires_at=expires, attempts_left=settings.sign_code_max_attempts,
                            code=code if settings.demo_show_sign_code else None)


def sign(user: User, app_id: str, code: str) -> ApplicationClient:
    app = _get_own(user, app_id)
    if app.status != S.signing or app.signing is None:
        raise conflict("not_signing", "Договор сейчас не на подписании")
    stored = state.sign_codes.get(app.id)
    if stored is None:
        raise conflict("code_not_requested", "Сначала запросите код подписи")
    code_hash, expires, attempts = stored
    if _now() > expires:
        state.sign_codes.pop(app.id, None)
        raise conflict("code_expired", "Срок действия кода истёк — запросите новый")
    if _hash(code) != code_hash:
        attempts -= 1
        if attempts <= 0:
            state.sign_codes.pop(app.id, None)
            raise conflict("code_attempts_exceeded", "Попытки закончились — запросите новый код")
        state.sign_codes[app.id] = (code_hash, expires, attempts)
        raise ApiError(422, "invalid_code", f"Код не подходит. Осталось попыток: {attempts}",
                       [FieldError(field="code", code="invalid_code", message="Неверный код")])

    state.sign_codes.pop(app.id, None)
    now = _now()
    app.signing.signed_at = now
    amount = app.offer.amount if app.offer else (app.amount or 0)
    app.issuance = Issuance(contract_number=app.signing.contract_number, signed_at=now, issued_at=now,
                            amount=amount, account=app.company.account)
    _move(app, S.issued, Actor.system,
          f"Договор подписан, деньги зачислены на счёт •••• {app.company.account[-4:]}")
    return to_client(app)


# --- [Аналитик]


def analyst_queue(status: S | None) -> list[AnalystQueueItem]:
    apps = [a for a in state.apps.values() if a.status != S.draft]
    if status is not None:
        apps = [a for a in apps if a.status == status]
    apps.sort(key=lambda a: a.created_at, reverse=True)
    return [
        AnalystQueueItem(
            id=a.id, company=CompanyShort(inn=a.company.inn, name=a.company.name, type=a.company.type),
            product_id=a.product_id, product_name=a.product_name, amount=a.amount, term_months=a.term_months,
            status=a.status, created_at=a.created_at, submitted_at=a.submitted_at,
            decision_outcome=a.decision.outcome if a.decision else None,
            decided_by=a.decision.decided_by if a.decision else None,
            followed_system=a.decision.followed_system if a.decision else None,
        )
        for a in apps
    ]


def analyst_get(app_id: str) -> ApplicationAnalyst:
    app = state.apps.get(app_id)
    if app is None or app.status == S.draft:
        raise not_found("application", "Заявка не найдена")
    return app


def analyst_decide(app_id: str, req: AnalystDecisionRequest) -> ApplicationAnalyst:
    app = analyst_get(app_id)
    if app.status not in (S.manual_review, S.docs_requested):
        raise conflict("decision_not_allowed", "Решение по заявке в этом статусе не принимается")

    errors: list[FieldError] = []
    comment = (req.comment_for_client or "").strip()
    if req.action != AnalystAction.approve and not comment:
        errors.append(FieldError(field="commentForClient", code="required", message="Добавьте комментарий для клиента"))
    if req.action == AnalystAction.counter_offer:
        if req.amount is None or not (0 < req.amount < (app.amount or 0)):
            errors.append(FieldError(field="amount", code="out_of_range",
                                     message="Сумма контрпредложения должна быть меньше запрошенной"))
    if req.action == AnalystAction.reject and req.reason_code not in REJECT_REASONS:
        errors.append(FieldError(field="reasonCode", code="required", message="Выберите причину отказа"))
    if req.action == AnalystAction.request_docs and not req.info_items:
        errors.append(FieldError(field="infoItems", code="required", message="Укажите, что запросить у клиента"))
    if errors:
        raise validation_error(errors)

    now = _now()
    recommended = app.system_recommendation.outcome if app.system_recommendation else None

    if req.action == AnalystAction.request_docs:
        app.info_request = InfoRequest(requested_at=now, comment=comment, items=req.info_items or [])
        _move(app, S.docs_requested, Actor.analyst, comment)
        return app

    outcome = {
        AnalystAction.approve: DecisionOutcome.approved,
        AnalystAction.counter_offer: DecisionOutcome.counter_offer,
        AnalystAction.reject: DecisionOutcome.rejected,
    }[req.action]
    approved_amount = {AnalystAction.approve: app.amount, AnalystAction.counter_offer: req.amount}.get(req.action)
    followed = recommended == outcome or (recommended == DecisionOutcome.manual_review and outcome == DecisionOutcome.approved)
    app.decision = Decision(outcome=outcome, requested_amount=app.amount or 0, approved_amount=approved_amount,
                            decided_by=DecidedBy.analyst, decided_at=now, comment_for_client=comment or None,
                            reason_code=req.reason_code, followed_system=followed)

    if outcome in (DecisionOutcome.approved, DecisionOutcome.counter_offer) and approved_amount:
        product = PRODUCTS_BY_ID[app.product_id]
        rb = app.rate_breakdown or RateBreakdown(key_rate=KEY_RATE, product_spread=product.spread,
                                                 risk_premium=0, rate=product.rate_from)
        term = app.term_months or product.max_term_months
        app.offer = Offer(
            type=OfferType.approved if outcome == DecisionOutcome.approved else OfferType.counter_offer,
            amount=approved_amount, term_months=term, rate=rb.rate, rate_breakdown=rb,
            monthly_payment=annuity_payment(approved_amount, rb.rate, term),
            collateral_required=Collateral.none,
            valid_until=now + timedelta(days=get_settings().offer_ttl_days),
            requested=OfferRequested(amount=app.amount or 0, term_months=term,
                                     collateral=app.collateral or Collateral.none),
        )
        status = S.approved if outcome == DecisionOutcome.approved else S.counter_offer
    else:
        status = S.rejected
    _move(app, status, Actor.analyst, comment or None)
    return app
