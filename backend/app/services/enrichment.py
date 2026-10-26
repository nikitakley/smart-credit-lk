"""Обогащение заявки: данные о клиенте из внутренних и внешних источников → проверки (checks).

Источники:
  bank  — обороты по расчётному счёту (внутренние данные банка, без сетевых запросов);
  egrul — ЕГРЮЛ / ЕГРИП: существует ли бизнес и действует ли;
  nbki  — бюро кредитных историй: долговая нагрузка и платёжная дисциплина;
  pb    — ФНС «Прозрачный бизнес»: признаки риска.

Каждый источник превращается в проверку со статусом:
  ok — препятствий нет; warning — нужно внимание; fail — стоп-фактор; unavailable — источник не ответил.
Правила оценки — простые функции без сети и базы: их легко проверить тестами и объяснить.
Этот же модуль на этапе 4 вызывает конвейер; сейчас — специалист кнопкой «Обновить данные».
"""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx2 as httpx
from sqlalchemy.orm import Session

from app.db import models
from app.errors import conflict
from app.integrations.egr import RegistryInfo, fetch_registry_info
from app.integrations.http import SourceUnavailable
from app.integrations.nbki import CreditHistory, fetch_credit_history
from app.integrations.pb import RiskProfile, fetch_risk_profile
from app.schemas.enums import ApplicationStatus, CheckSource, CheckStatus, CompanyType
from app.services import analyst
from app.services.common import commit, now
from app.services.text import plural, rub

CHECK_TITLES = {
    CheckSource.bank: "Обороты по счёту в банке",
    CheckSource.egrul: "ЕГРЮЛ / ЕГРИП",
    CheckSource.pb: "ФНС «Прозрачный бизнес»",
    CheckSource.nbki: "Бюро кредитных историй",
}

# В каких статусах специалист может повторно запросить данные: заявка уже прошла подачу
# и ещё не получила окончательного решения
REFRESH_ALLOWED = {
    ApplicationStatus.enrichment,
    ApplicationStatus.scoring,
    ApplicationStatus.manual_review,
    ApplicationStatus.docs_requested,
}

MONTHS = ("месяц", "месяца", "месяцев")
COMPANIES_AT = ("компании", "компаний", "компаний")  # «у 54 компаний»
COMPANIES_IN = ("компании", "компаниях", "компаниях")  # «в 12 компаниях»


@dataclass(frozen=True)
class CheckResult:
    source: CheckSource
    status: CheckStatus
    summary: str
    details: dict[str, Any]


@dataclass(frozen=True)
class BankData:
    monthly_revenue: int
    revenue_growth: Decimal
    history_months: int


@dataclass(frozen=True)
class EnrichmentInput:
    """Всё, что нужно для запросов, — обычные значения, а не объекты базы (см. refresh_checks)."""

    inn: str
    company_type: CompanyType
    consent_given_at: datetime
    bank: BankData | None


def _result(source: CheckSource, status: CheckStatus, summary: str, data: Any = None) -> CheckResult:
    # details хранятся как есть и так же отдаются аналитику, поэтому сразу в формате API (camelCase)
    details = data.model_dump(mode="json", by_alias=True) if data is not None else {}
    return CheckResult(source, status, summary, details)


# --- [Правила оценки по источникам]


def bank_check(bank: BankData | None) -> CheckResult:
    source = CheckSource.bank
    if bank is None:
        return CheckResult(source, CheckStatus.warning, "Нет данных об оборотах по счёту в банке", {})
    details = {
        "monthlyRevenue": bank.monthly_revenue,
        "revenueGrowth": float(bank.revenue_growth),
        "historyMonths": bank.history_months,
    }
    growth = round(bank.revenue_growth)
    if bank.history_months < 6:
        months = bank.history_months
        summary = f"Обороты по счёту только за {months} {plural(months, MONTHS)} — недостаточно для оценки"
        return CheckResult(source, CheckStatus.warning, summary, details)
    if growth <= -30:
        return CheckResult(source, CheckStatus.warning, f"Обороты по счёту за 12 месяцев снизились на {-growth}%", details)
    if growth >= 10:
        return CheckResult(source, CheckStatus.ok, f"Выручка за 12 месяцев выросла на {growth}%", details)
    return CheckResult(source, CheckStatus.ok, "Обороты по счёту стабильны", details)


def registry_check(info: RegistryInfo) -> CheckResult:
    source = CheckSource.egrul
    if not info.found:
        return _result(source, CheckStatus.fail, "Компания не найдена в ЕГРЮЛ / ЕГРИП", info)
    entrepreneur = info.registry == "egrip"
    stop_factors = {
        "liquidated": "Деятельность предпринимателя прекращена" if entrepreneur else "Компания ликвидирована",
        "liquidating": "Компания в процессе ликвидации",
        "bankrupt": "Компания признана банкротом",
    }
    if info.status in stop_factors:
        return _result(source, CheckStatus.fail, stop_factors[info.status], info)
    if info.status == "reorganizing":
        return _result(source, CheckStatus.warning, "Компания в процессе реорганизации", info)
    if info.age_months is not None and info.age_months < 6:
        months = info.age_months
        return _result(source, CheckStatus.warning, f"Бизнес зарегистрирован {months} {plural(months, MONTHS)} назад", info)
    if entrepreneur:
        return _result(source, CheckStatus.ok, "Предприниматель зарегистрирован, деятельность ведётся", info)
    return _result(source, CheckStatus.ok, "Компания действует", info)


def credit_history_check(history: CreditHistory) -> CheckResult:
    source = CheckSource.nbki
    if not history.history_found:
        return _result(source, CheckStatus.warning, "Кредитной истории в бюро нет", history)
    if history.current_overdue > 0:
        return _result(source, CheckStatus.fail, f"Текущая просроченная задолженность — {rub(history.current_overdue)}", history)
    if history.overdues_90_plus > 0:
        return _result(source, CheckStatus.fail, "Просрочки более 90 дней за последние 24 месяца", history)
    if history.overdues_30_to_89 > 0:
        n = history.overdues_30_to_89
        return _result(source, CheckStatus.warning, f"Просрочки от 30 до 89 дней за 24 месяца: {n}", history)
    if history.inquiries_last_month >= 5:
        n = history.inquiries_last_month
        return _result(source, CheckStatus.warning, f"Много запросов кредитной истории за 30 дней: {n}", history)
    if history.overdues_up_to_29 > 0:
        summary = f"Просрочки до 30 дней за 24 месяца: {history.overdues_up_to_29}, серьёзных нет"
    elif history.history_months < 12:
        summary = "Кредитная история короткая, просрочек нет"
    elif history.monthly_payments > 0:
        summary = f"Просрочек нет, платежи по кредитам — {rub(history.monthly_payments)} в месяц"
    else:
        summary = "Просрочек за 24 месяца нет"
    return _result(source, CheckStatus.ok, summary, history)


def risk_check(profile: RiskProfile) -> CheckResult:
    source = CheckSource.pb
    if not profile.found:
        return _result(source, CheckStatus.warning, "Сведения в «Прозрачном бизнесе» не найдены", profile)
    if profile.disqualified_persons:
        return _result(source, CheckStatus.fail, "В органах управления есть дисквалифицированные лица", profile)
    signals = []
    if n := profile.mass_address_companies:
        signals.append(f"Адрес регистрации указан у {n} {plural(n, COMPANIES_AT)} (массовый адрес)")
    if n := profile.mass_head_companies:
        signals.append(f"Руководитель указан в {n} {plural(n, COMPANIES_IN)} (массовый руководитель)")
    if profile.unreliable_info:
        signals.append("Недостоверные сведения в реестре: " + ", ".join(profile.unreliable_info))
    if profile.tax_arrears:
        signals.append(f"Задолженность по налогам — {rub(profile.tax_arrears)}")
    if profile.reporting_overdue:
        signals.append("Не сдаёт налоговую отчётность более года")
    if signals:
        return _result(source, CheckStatus.warning, "; ".join(signals), profile)
    return _result(source, CheckStatus.ok, "Признаков риска не выявлено", profile)


def unavailable_check(source: CheckSource, reason: str) -> CheckResult:
    return CheckResult(
        source, CheckStatus.unavailable, "Источник временно не ответил — данные будут запрошены повторно",
        {"reason": reason},
    )


# --- [Сбор данных]


def collect_checks(client: httpx.Client, data: EnrichmentInput) -> list[CheckResult]:
    """Опросить все источники. Недоступность одного источника не прерывает остальные."""
    external: dict[CheckSource, Callable[[], CheckResult]] = {
        CheckSource.egrul: lambda: registry_check(fetch_registry_info(client, data.inn)),
        CheckSource.nbki: lambda: credit_history_check(
            fetch_credit_history(client, data.inn, data.company_type, data.consent_given_at)
        ),
        CheckSource.pb: lambda: risk_check(fetch_risk_profile(client, data.inn)),
    }
    # Внешние источники опрашиваются параллельно: общее время — как у самого медленного, а не сумма
    with ThreadPoolExecutor(max_workers=len(external), thread_name_prefix="enrichment") as pool:
        futures = {source: pool.submit(task) for source, task in external.items()}

    results = [bank_check(data.bank)]
    for source, future in futures.items():
        try:
            results.append(future.result())
        except SourceUnavailable as exc:
            results.append(unavailable_check(source, exc.reason))
    return results


def enrichment_input(app: models.Application) -> EnrichmentInput:
    if app.submitted_at is None:
        raise conflict("not_submitted", "Заявка ещё не подана: согласия на запрос данных нет")
    profile = app.company.bank_profile
    return EnrichmentInput(
        inn=app.company.inn,
        company_type=app.company.type,
        consent_given_at=app.submitted_at,  # согласия даются при подаче заявки
        bank=BankData(profile.monthly_revenue, profile.revenue_growth, profile.history_months) if profile else None,
    )


def save_checks(app: models.Application, results: list[CheckResult], fetched_at: datetime) -> None:
    """Записать проверки: по каждому источнику одна запись, при повторе — обновляется."""
    existing = {check.source: check for check in app.checks}
    for result in results:
        check = existing.get(result.source)
        if check is None:
            check = models.Check(source=result.source, title=CHECK_TITLES[result.source])
            app.checks.append(check)
        check.status = result.status
        check.summary = result.summary
        check.details = result.details
        check.fetched_at = fetched_at


def refresh_checks(db: Session, application_id: str, client: httpx.Client) -> models.Application:
    """Повторно запросить данные из источников по заявке (действие специалиста)."""
    app = analyst.get(db, application_id)
    if app.status not in REFRESH_ALLOWED:
        raise conflict("checks_refresh_not_allowed", "В этом статусе данные из источников не запрашиваются")
    data = enrichment_input(app)
    version = app.version
    # Завершаем транзакцию чтения ДО сетевых запросов: соединение с базой не должно простаивать
    # секунды, пока отвечают внешние сервисы, — иначе пул соединений быстро закончится
    db.rollback()

    results = collect_checks(client, data)

    app = analyst.get(db, application_id)
    if app.version != version:  # пока ждали источники, заявку изменили — не затираем чужие изменения
        raise conflict("concurrent_update", "Заявку только что изменили — обновите страницу и повторите действие")
    save_checks(app, results, now())
    app.updated_at = now()  # изменение самой заявки: увеличит version и сработает оптимистичная блокировка
    commit(db)
    return analyst.get(db, application_id)
