"""НБКИ: кредитная история. Запрос только с согласием заёмщика (дано при подаче заявки)."""

from datetime import datetime

import httpx2 as httpx
from pydantic import BaseModel

from app.config import get_settings
from app.integrations.http import SourceUnavailable, parse_response, request_json
from app.schemas.checks import CreditHistoryDetails, UnavailableReason
from app.schemas.enums import CompanyType

SOURCE = "nbki"


# --- [Формат источника]


class _Loan(BaseModel):
    type: str
    status: str
    balance: int
    monthly_payment: int
    current_overdue: int = 0


class _Discipline(BaseModel):
    overdue_1_29: int = 0
    overdue_30_59: int = 0
    overdue_60_89: int = 0
    overdue_90_plus: int = 0


class _Report(BaseModel):
    report_id: str
    history_found: bool
    score: int | None = None
    history_length_months: int = 0
    loans: list[_Loan] = []
    payment_discipline_24m: _Discipline = _Discipline()
    inquiries_30d: int = 0


# --- [Перевод во внутренний формат банка (app/schemas/checks.py)]


def fetch_credit_history(
    client: httpx.Client, inn: str, company_type: CompanyType, consent_given_at: datetime
) -> CreditHistoryDetails:
    payload = {
        "inn": inn,
        "subject_type": "legal_entity" if company_type == CompanyType.legal else "individual_entrepreneur",
        "consent": {"given": True, "given_at": consent_given_at.isoformat(), "purpose": "loan_application"},
    }
    data = request_json(client, SOURCE, "POST", f"{get_settings().nbki_base_url}/v1/credit-reports", json=payload)
    if data is None:  # у бюро 404 не бывает: отсутствие истории — это отчёт с history_found=false
        raise SourceUnavailable(SOURCE, UnavailableReason.invalid_response, 404)
    report = parse_response(SOURCE, _Report, data)
    active = [loan for loan in report.loans if loan.status == "active"]
    d = report.payment_discipline_24m
    overdues_30_to_89 = d.overdue_30_59 + d.overdue_60_89
    return CreditHistoryDetails(
        report_id=report.report_id,
        history_found=report.history_found,
        bureau_score=report.score,
        history_months=report.history_length_months,
        active_loans=len(active),
        total_debt=sum(loan.balance for loan in active),
        monthly_payments=sum(loan.monthly_payment for loan in active),
        current_overdue=sum(loan.current_overdue for loan in active),
        overdues_up_to_29=d.overdue_1_29,
        overdues_30_to_89=overdues_30_to_89,
        overdues_90_plus=d.overdue_90_plus,
        overdues_24m=d.overdue_1_29 + overdues_30_to_89 + d.overdue_90_plus,
        inquiries_last_month=report.inquiries_30d,
    )
