"""НБКИ: кредитный отчёт. Запрос возможен только с согласием субъекта кредитной истории."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter

from simulator.errors import SourceError
from simulator.faults import Source
from simulator.models import CreditReport, CreditReportRequest, ErrorResponse
from simulator.security import source_guard
from simulator.store import get_store

router = APIRouter(prefix="/nbki/v1", tags=["НБКИ"], dependencies=[source_guard(Source.nbki)])

# Согласие заёмщика на запрос кредитной истории действует ограниченное время
CONSENT_VALIDITY = timedelta(days=183)


@router.post(
    "/credit-reports",
    response_model=CreditReport,
    summary="Кредитный отчёт по ИНН",
    description="Если кредитной истории нет, возвращается отчёт с historyFound=false — это результат, а не ошибка.",
    responses={
        400: {"model": ErrorResponse, "description": "Неверный запрос"},
        403: {"model": ErrorResponse, "description": "Нет действующего согласия субъекта"},
    },
)
async def credit_report(body: CreditReportRequest) -> CreditReport:
    expected_type = "legal_entity" if len(body.inn) == 10 else "individual_entrepreneur"
    if body.subject_type != expected_type:
        raise SourceError(400, "subject_type_mismatch", f"Для ИНН из {len(body.inn)} цифр ожидается {expected_type}")
    now = datetime.now(UTC)
    if not body.consent.given:
        raise SourceError(403, "consent_required", "Нет согласия субъекта на запрос кредитной истории")
    if now - body.consent.given_at > CONSENT_VALIDITY:
        raise SourceError(403, "consent_expired", "Срок действия согласия истёк")

    report_id = f"NBKI-{now:%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"
    record = get_store().nbki.get(body.inn)
    if record is None:
        return CreditReport(report_id=report_id, generated_at=now, inn=body.inn, history_found=False)
    return CreditReport(report_id=report_id, generated_at=now, history_found=True, **record.model_dump())
