"""ФНС «Прозрачный бизнес»: признаки риска, налоговый режим, численность, отчётность."""

import httpx2 as httpx
from pydantic import BaseModel

from app.config import get_settings
from app.integrations.http import parse_response, request_json
from app.schemas.checks import RiskDetails

SOURCE = "pb"

UNRELIABLE_LABELS = {"address": "адрес", "head": "руководитель", "founder": "учредитель"}


# --- [Формат источника]


class _Marker(BaseModel):
    flag: bool
    companies_count: int


class _TaxArrears(BaseModel):
    has_arrears: bool
    amount: int = 0


class _FinancialYear(BaseModel):
    year: int
    revenue: int
    net_profit: int


class _Profile(BaseModel):
    tax_regime: str
    employees_avg: int | None = None
    mass_address: _Marker
    mass_head: _Marker
    disqualified_persons: bool
    unreliable_info: list[str] = []
    tax_arrears: _TaxArrears
    reporting_overdue: bool
    financials: list[_FinancialYear] = []


# --- [Перевод во внутренний формат банка (app/schemas/checks.py)]


def fetch_risk_profile(client: httpx.Client, inn: str) -> RiskDetails:
    data = request_json(client, SOURCE, "GET", f"{get_settings().pb_base_url}/v1/companies/{inn}")
    if data is None:
        return RiskDetails(found=False)
    profile = parse_response(SOURCE, _Profile, data)
    last_year = max(profile.financials, key=lambda f: f.year, default=None)
    return RiskDetails(
        found=True,
        tax_regime=profile.tax_regime,
        employees=profile.employees_avg,
        mass_address_companies=profile.mass_address.companies_count if profile.mass_address.flag else None,
        mass_head_companies=profile.mass_head.companies_count if profile.mass_head.flag else None,
        disqualified_persons=profile.disqualified_persons,
        unreliable_info=[UNRELIABLE_LABELS.get(item, item) for item in profile.unreliable_info],
        tax_arrears=profile.tax_arrears.amount if profile.tax_arrears.has_arrears else 0,
        reporting_overdue=profile.reporting_overdue,
        report_year=last_year.year if last_year else None,
        revenue=last_year.revenue if last_year else None,
        net_profit=last_year.net_profit if last_year else None,
    )
