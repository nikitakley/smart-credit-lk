"""Сервис заявок клиента: черновик, отправка, ответ на запрос, оффер, подписание."""

import hashlib
import hmac
import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.db import models
from app.db.models import application_number_seq
from app.errors import ApiError, FieldError, conflict, not_found, validation_error
from app.schemas.actions import SignCodeResponse
from app.schemas.application import ApplicationCreate, InfoResponseRequest, SubmitRequest
from app.schemas.auth import User
from app.schemas.enums import TERMINAL_STATUSES, Actor, ApplicationStatus, Collateral
from app.services.common import commit, load_application, now
from app.services.mappers import company_to_schema
from app.services.state_machine import transition

# --- [Чтение]


def get_company(db: Session, inn: str) -> models.Company:
    company = db.get(models.Company, inn)
    if company is None:
        raise not_found("company", "Компания не найдена")
    return company


def list_products(db: Session) -> list[models.Product]:
    return list(db.scalars(select(models.Product).where(models.Product.is_active).order_by(models.Product.min_amount)))


def get_own(db: Session, user: User, application_id: str) -> models.Application:
    app = load_application(db, application_id)
    # Чужую заявку не показываем — отвечаем так же, как на несуществующую
    if app is None or app.company_inn != user.inn:
        raise not_found("application", "Заявка не найдена")
    return app


def list_own(db: Session, user: User) -> list[models.Application]:
    query = (
        select(models.Application)
        .options(joinedload(models.Application.product))
        .where(models.Application.company_inn == user.inn)
        .order_by(models.Application.created_at.desc())
    )
    return list(db.scalars(query))


def current_application_id(db: Session, inn: str) -> str | None:
    query = (
        select(models.Application.id)
        .where(models.Application.company_inn == inn, models.Application.status.not_in(TERMINAL_STATUSES))
        .order_by(models.Application.updated_at.desc())
        .limit(1)
    )
    return db.scalar(query)


# --- [Черновик]


def _check_product(db: Session, product_id: str | None) -> None:
    if product_id is None:
        return
    product = db.get(models.Product, product_id)
    if product is None or not product.is_active:
        raise validation_error([FieldError(field="productId", code="unknown_product", message="Такого продукта нет")])


def create_draft(db: Session, user: User, data: ApplicationCreate) -> models.Application:
    _check_product(db, data.product_id)
    number = db.scalar(application_number_seq.next_value())
    app = models.Application(
        id=f"A-{number}",
        company_inn=user.inn,
        status=ApplicationStatus.draft,
        product_id=data.product_id,
        amount=data.amount,
        term_months=data.term_months,
        purpose=data.purpose,
        collateral=data.collateral,
        contact=data.contact.model_dump() if data.contact else None,
    )
    db.add(app)
    commit(db)
    return get_own(db, user, app.id)


def update_draft(db: Session, user: User, application_id: str, data: ApplicationCreate) -> models.Application:
    app = get_own(db, user, application_id)
    if app.status != ApplicationStatus.draft:
        raise conflict("not_draft", "Изменять можно только черновик")
    _check_product(db, data.product_id)
    for field in data.model_fields_set:  # только поля, которые клиент прислал (PATCH)
        value = getattr(data, field)
        setattr(app, field, value.model_dump() if field == "contact" and value is not None else value)
    commit(db)
    return get_own(db, user, application_id)


# --- [Отправка]


def _validate_for_submit(app: models.Application, data: SubmitRequest) -> None:
    errors: list[FieldError] = []
    required = [("product_id", "productId"), ("amount", "amount"), ("term_months", "termMonths"),
                ("purpose", "purpose"), ("contact", "contact")]
    for field, label in required:
        if getattr(app, field) is None:
            errors.append(FieldError(field=label, code="required", message="Обязательное поле"))

    product = app.product
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


def submit(
    db: Session, user: User, application_id: str, data: SubmitRequest, idempotency_key: str | None
) -> models.Application:
    if idempotency_key:
        saved = db.get(models.IdempotencyKey, idempotency_key)
        if saved is not None and saved.account_id == user.account_id:
            return get_own(db, user, saved.application_id)  # повторный запрос — тот же результат

    app = get_own(db, user, application_id)
    if app.status != ApplicationStatus.draft:
        raise conflict("not_draft", "Заявка уже отправлена")
    _validate_for_submit(app, data)

    app.consents = data.consents.model_dump()
    app.collateral = app.collateral or Collateral.none
    app.company_snapshot = company_to_schema(app.company).model_dump(mode="json")
    app.submitted_at = now()
    transition(app, ApplicationStatus.submitted, Actor.client, actor_account_id=user.account_id,
               note="Заявка отправлена в банк")
    if idempotency_key:
        db.add(models.IdempotencyKey(key=idempotency_key, account_id=user.account_id, application_id=app.id))
    commit(db)
    return get_own(db, user, application_id)


def respond_info(db: Session, user: User, application_id: str, data: InfoResponseRequest) -> models.Application:
    app = get_own(db, user, application_id)
    request = app.info_requests[-1] if app.info_requests else None
    if app.status != ApplicationStatus.docs_requested or request is None or request.responded_at is not None:
        raise conflict("no_info_request", "Банк не запрашивал дополнительную информацию")

    given = {a.code for a in data.answers if a.value.strip()}
    missing = [item for item in request.items if item.get("required", True) and item["code"] not in given]
    if missing:
        raise validation_error(
            [FieldError(field=f"answers.{item['code']}", code="required", message=item["label"]) for item in missing]
        )

    request.answers = [a.model_dump() for a in data.answers] + (
        [{"code": "comment", "value": data.comment}] if data.comment else []
    )
    request.responded_at = now()
    transition(app, ApplicationStatus.validation, Actor.client, actor_account_id=user.account_id,
               note="Клиент предоставил дополнительную информацию")
    commit(db)
    return get_own(db, user, application_id)


# ---------- Предложение банка ----------


def _active_offer(app: models.Application) -> models.Offer:
    offer = app.offers[-1] if app.offers else None
    if app.status not in (ApplicationStatus.approved, ApplicationStatus.counter_offer) or offer is None:
        raise conflict("no_offer", "Нет действующего предложения банка")
    if offer.valid_until < now():
        raise conflict("offer_expired", "Срок действия предложения истёк")
    return offer


def accept_offer(db: Session, user: User, application_id: str) -> models.Application:
    app = get_own(db, user, application_id)
    offer = _active_offer(app)
    number = f"КД-{app.id.removeprefix('A-')}/{now().year}"
    app.contract = models.Contract(contract_number=number, amount=offer.amount, account=app.company.account)
    transition(app, ApplicationStatus.signing, Actor.client, actor_account_id=user.account_id,
               note=f"Предложение принято, сформирован договор {number}")
    commit(db)
    return get_own(db, user, application_id)


def decline_offer(db: Session, user: User, application_id: str) -> models.Application:
    app = get_own(db, user, application_id)
    _active_offer(app)
    transition(app, ApplicationStatus.declined_by_client, Actor.client, actor_account_id=user.account_id,
               note="Клиент отказался от предложения")
    commit(db)
    return get_own(db, user, application_id)


# ---------- Подписание ----------


def _hash(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _signing_application(db: Session, user: User, application_id: str) -> models.Application:
    app = get_own(db, user, application_id)
    if app.status != ApplicationStatus.signing or app.contract is None:
        raise conflict("not_signing", "Договор сейчас не на подписании")
    return app


def _active_code(db: Session, application_id: str) -> models.SignCode | None:
    query = (
        select(models.SignCode)
        .where(models.SignCode.application_id == application_id, models.SignCode.used_at.is_(None))
        .order_by(models.SignCode.id.desc())
        .limit(1)
    )
    return db.scalar(query)


def request_sign_code(db: Session, user: User, application_id: str) -> SignCodeResponse:
    settings = get_settings()
    app = _signing_application(db, user, application_id)

    # Предыдущие коды больше не действуют
    if (old := _active_code(db, app.id)) is not None:
        old.used_at = now()

    code = f"{secrets.randbelow(1_000_000):06d}"  # криптостойкий генератор
    sent_at = now()
    expires_at = sent_at + timedelta(seconds=settings.sign_code_ttl_seconds)
    db.add(models.SignCode(application_id=app.id, code_hash=_hash(code),
                           attempts_left=settings.sign_code_max_attempts, expires_at=expires_at))
    app.contract.code_sent_at = sent_at
    commit(db)
    return SignCodeResponse(sent_at=sent_at, expires_at=expires_at, attempts_left=settings.sign_code_max_attempts,
                            code=code if settings.demo_show_sign_code else None)


def sign(db: Session, user: User, application_id: str, code: str) -> models.Application:
    app = _signing_application(db, user, application_id)
    sign_code = _active_code(db, app.id)
    if sign_code is None:
        raise conflict("code_not_requested", "Сначала запросите код подписи")
    if now() > sign_code.expires_at:
        sign_code.used_at = now()
        commit(db)
        raise conflict("code_expired", "Срок действия кода истёк — запросите новый")

    # Сравнение за постоянное время: по времени ответа нельзя подобрать код посимвольно
    if not hmac.compare_digest(_hash(code), sign_code.code_hash):
        sign_code.attempts_left -= 1
        if sign_code.attempts_left <= 0:
            sign_code.used_at = now()
            commit(db)
            raise conflict("code_attempts_exceeded", "Попытки закончились — запросите новый код")
        commit(db)
        raise ApiError(422, "invalid_code", f"Код не подходит. Осталось попыток: {sign_code.attempts_left}",
                       [FieldError(field="code", code="invalid_code", message="Неверный код")])

    signed_at = now()
    sign_code.used_at = signed_at
    app.contract.signed_at = signed_at
    # Выдача средств смоделирована: деньги «зачисляются» сразу после подписания (этап 5 — мок выдачи)
    app.contract.issued_at = signed_at
    transition(app, ApplicationStatus.issued, Actor.system,
               note=f"Договор подписан, деньги зачислены на счёт •••• {app.contract.account[-4:]}")
    commit(db)
    return get_own(db, user, application_id)
