"""НБКИ: кредитная история. Запрос только с согласием заёмщика (дано при подаче заявки)."""

from datetime import datetime

import httpx2 as httpx
from pydantic import BaseModel, computed_field

from app.config import get_settings
from app.integrations.http import SourceUnavailable, parse_response, request_json
from app.schemas.base import CamelModel
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


# --- [Внутренний формат банка]


class CreditHistory(CamelModel):
    report_id: str
    history_found: bool
    bureau_score: int | None = None
    history_months: int = 0
    active_loans: int = 0
    total_debt: int = 0
    monthly_payments: int = 0  # платежи по действующим кредитам, ₽/мес — входит в долговую нагрузку
    current_overdue: int = 0
    # Число просрочек за последние 24 месяца по длительности
    overdues_up_to_29: int = 0
    overdues_30_to_89: int = 0
    overdues_90_plus: int = 0
    inquiries_last_month: int = 0  # сколько раз историю запрашивали за 30 дней

    @computed_field(alias="overdues24m")  # попадает и в JSON: скорингу нужно общее число просрочек
    @property
    def overdues_24m(self) -> int:
        return self.overdues_up_to_29 + self.overdues_30_to_89 + self.overdues_90_plus


def fetch_credit_history(
    client: httpx.Client, inn: str, company_type: CompanyType, consent_given_at: datetime
) -> CreditHistory:
    payload = {
        "inn": inn,
        "subject_type": "legal_entity" if company_type == CompanyType.legal else "individual_entrepreneur",
        "consent": {"given": True, "given_at": consent_given_at.isoformat(), "purpose": "loan_application"},
    }
    data = request_json(client, SOURCE, "POST", f"{get_settings().nbki_base_url}/v1/credit-reports", json=payload)
    if data is None:  # у бюро 404 не бывает: отсутствие истории — это отчёт с history_found=false
        raise SourceUnavailable(SOURCE, "unexpected_404")
    report = parse_response(SOURCE, _Report, data)
    active = [loan for loan in report.loans if loan.status == "active"]
    discipline = report.payment_discipline_24m
    return CreditHistory(
        report_id=report.report_id,
        history_found=report.history_found,
        bureau_score=report.score,
        history_months=report.history_length_months,
        active_loans=len(active),
        total_debt=sum(loan.balance for loan in active),
        monthly_payments=sum(loan.monthly_payment for loan in active),
        current_overdue=sum(loan.current_overdue for loan in active),
        overdues_up_to_29=discipline.overdue_1_29,
        overdues_30_to_89=discipline.overdue_30_59 + discipline.overdue_60_89,
        overdues_90_plus=discipline.overdue_90_plus,
        inquiries_last_month=report.inquiries_30d,
    )
