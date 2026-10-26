"""Обогащение заявки: правила оценки источников, согласованность с демо-данными, действие специалиста."""

from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.seed import SeedApplication, SeedCompany, read_seed
from app.db.session import SessionLocal
from app.integrations.egr import RegistryInfo
from app.integrations.http import get_integration_client
from app.integrations.nbki import CreditHistory
from app.integrations.pb import RiskProfile
from app.main import app
from app.schemas.enums import CheckSource, CheckStatus
from app.services import enrichment
from app.services.common import commit, load_application
from app.services.enrichment import BankData, EnrichmentInput, collect_checks
from app.services.text import plural, rub
from tests.conftest import login

SEED_DIR = get_settings().seed_dir
COMPANIES = {c.inn: c for c in read_seed("companies.json", SeedCompany, SEED_DIR)}
DEMO_WITH_CHECKS = [a for a in read_seed("demo_applications.json", SeedApplication, SEED_DIR) if a.checks]


def enrichment_input(company: SeedCompany) -> EnrichmentInput:
    profile = company.bank_profile
    return EnrichmentInput(
        inn=company.inn,
        company_type=company.type,
        consent_given_at=datetime.now(UTC),
        bank=BankData(profile.monthly_revenue, profile.revenue_growth, profile.history_months),
    )


# --- [Правила оценки (чистые функции, без сети и базы)]


def test_text_helpers() -> None:
    assert rub(1_500_000) == "1 500 000 ₽"
    months = ("месяц", "месяца", "месяцев")
    assert [plural(n, months) for n in (1, 4, 5, 11, 21, 22, 112)] == [
        "месяц", "месяца", "месяцев", "месяцев", "месяц", "месяца", "месяцев"
    ]


@pytest.mark.parametrize(
    ("bank", "status", "summary"),
    [
        (None, CheckStatus.warning, "Нет данных об оборотах по счёту в банке"),
        (BankData(400_000, Decimal(0), 4), CheckStatus.warning, "Обороты по счёту только за 4 месяца — недостаточно для оценки"),
        (BankData(400_000, Decimal(-45), 30), CheckStatus.warning, "Обороты по счёту за 12 месяцев снизились на 45%"),
        (BankData(400_000, Decimal(12), 30), CheckStatus.ok, "Выручка за 12 месяцев выросла на 12%"),
        (BankData(400_000, Decimal(3), 30), CheckStatus.ok, "Обороты по счёту стабильны"),
    ],
)
def test_bank_check(bank: BankData | None, status: CheckStatus, summary: str) -> None:
    result = enrichment.bank_check(bank)
    assert (result.status, result.summary) == (status, summary)


@pytest.mark.parametrize(
    ("info", "status"),
    [
        (RegistryInfo(found=False), CheckStatus.fail),
        (RegistryInfo(found=True, registry="egrul", status="liquidating", age_months=40), CheckStatus.fail),
        (RegistryInfo(found=True, registry="egrul", status="bankrupt", age_months=40), CheckStatus.fail),
        (RegistryInfo(found=True, registry="egrul", status="reorganizing", age_months=40), CheckStatus.warning),
        (RegistryInfo(found=True, registry="egrip", status="active", age_months=2), CheckStatus.warning),
        (RegistryInfo(found=True, registry="egrip", status="active", age_months=20), CheckStatus.ok),
    ],
)
def test_registry_check(info: RegistryInfo, status: CheckStatus) -> None:
    assert enrichment.registry_check(info).status == status


@pytest.mark.parametrize(
    ("history", "status"),
    [
        (CreditHistory(report_id="r", history_found=False), CheckStatus.warning),
        (CreditHistory(report_id="r", history_found=True, history_months=40, current_overdue=15_000), CheckStatus.fail),
        (CreditHistory(report_id="r", history_found=True, history_months=40, overdues_90_plus=1), CheckStatus.fail),
        (CreditHistory(report_id="r", history_found=True, history_months=40, overdues_30_to_89=2), CheckStatus.warning),
        (CreditHistory(report_id="r", history_found=True, history_months=40, inquiries_last_month=7), CheckStatus.warning),
        (CreditHistory(report_id="r", history_found=True, history_months=40, overdues_up_to_29=1), CheckStatus.ok),
    ],
)
def test_credit_history_check(history: CreditHistory, status: CheckStatus) -> None:
    assert enrichment.credit_history_check(history).status == status


def test_risk_check_lists_every_signal() -> None:
    result = enrichment.risk_check(RiskProfile(found=True, mass_head_companies=12, tax_arrears=5_000, reporting_overdue=True))
    assert result.status == CheckStatus.warning
    assert result.summary == (
        "Руководитель указан в 12 компаниях (массовый руководитель); "
        "Задолженность по налогам — 5 000 ₽; Не сдаёт налоговую отчётность более года"
    )
    assert enrichment.risk_check(RiskProfile(found=True, disqualified_persons=True)).status == CheckStatus.fail


# --- [Демо-данные согласованы с источниками]


@pytest.mark.parametrize("seed", DEMO_WITH_CHECKS, ids=lambda a: a.id)
def test_demo_checks_match_live_sources(seed: SeedApplication, simulator: TestClient) -> None:
    # Проверки в демо-заявках должны совпадать с тем, что дают настоящие правила и симулятор.
    # Иначе после «Обновить данные» демо-заявка вдруг поменяла бы картину.
    live = {r.source: r for r in collect_checks(simulator, enrichment_input(COMPANIES[seed.company_inn]))}
    for check in seed.checks:
        assert (live[check.source].status, live[check.source].summary) == (check.status, check.summary), check.source


def test_outage_of_one_source_keeps_others(simulator: TestClient) -> None:
    simulator.put("/admin/sources/nbki", json={"mode": "error"})
    results = {r.source: r for r in collect_checks(simulator, enrichment_input(COMPANIES["7810624578"]))}
    assert results[CheckSource.nbki].status == CheckStatus.unavailable
    assert results[CheckSource.nbki].details == {"reason": "http_503"}
    assert {results[s].status for s in (CheckSource.bank, CheckSource.egrul, CheckSource.pb)} == {CheckStatus.ok}


# --- [Действие специалиста: обновить данные из источников]


@pytest.fixture
def api(client: TestClient, simulator: TestClient) -> Iterator[TestClient]:
    """API, в котором вместо настоящего HTTP-клиента к источникам — симулятор в памяти."""
    app.dependency_overrides[get_integration_client] = lambda: simulator
    yield client
    app.dependency_overrides.clear()


def refresh(api: TestClient, app_id: str, headers: dict) -> dict:
    response = api.post(f"/api/analyst/applications/{app_id}/checks/refresh", headers=headers)
    return {"status_code": response.status_code, **response.json()}


def test_refresh_fills_checks_without_changing_status(api: TestClient, analyst: dict) -> None:
    before = api.get("/api/analyst/applications/A-1026", headers=analyst).json()
    assert {c["source"] for c in before["checks"]} == {"bank", "egrul"}  # конвейер «остановился» на обогащении

    after = refresh(api, "A-1026", analyst)
    assert after["status_code"] == 200
    assert after["status"] == "enrichment"
    assert {c["source"]: c["status"] for c in after["checks"]} == {"bank": "ok", "egrul": "ok", "nbki": "ok", "pb": "ok"}
    nbki = next(c for c in after["checks"] if c["source"] == "nbki")
    assert nbki["details"]["monthlyPayments"] == 750_000
    assert after["updatedAt"] > before["updatedAt"]


def test_refresh_hides_details_from_client(api: TestClient, analyst: dict) -> None:
    refresh(api, "A-1026", analyst)
    vektor = login(api, "vektor")
    checks = api.get("/api/applications/A-1026", headers=vektor).json()["checks"]
    assert len(checks) == 4
    assert all("details" not in c for c in checks)


def test_refresh_access_and_status_rules(api: TestClient, analyst: dict, prodmarket: dict) -> None:
    assert refresh(api, "A-1025", prodmarket)["status_code"] == 403
    assert refresh(api, "A-1020", analyst)["status_code"] == 404  # черновики специалисту не видны
    decided = refresh(api, "A-1022", analyst)
    assert decided["status_code"] == 409
    assert decided["error"]["code"] == "checks_refresh_not_allowed"


def test_refresh_detects_concurrent_change(api: TestClient, analyst: dict, monkeypatch) -> None:
    original = enrichment.collect_checks

    def collect_while_someone_edits(*args, **kwargs):
        # Пока банк ждёт ответы источников, заявку меняет другой запрос
        with SessionLocal() as other:
            application = load_application(other, "A-1025")
            application.term_months = 36
            commit(other)
        return original(*args, **kwargs)

    monkeypatch.setattr(enrichment, "collect_checks", collect_while_someone_edits)
    result = refresh(api, "A-1025", analyst)
    assert result["status_code"] == 409
    assert result["error"]["code"] == "concurrent_update"
