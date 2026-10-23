""""Справочники и перечисления, общие для API и бизнес-логики."""

from enum import StrEnum


class Role(StrEnum):
    client = "client"
    analyst = "analyst"


class CompanyType(StrEnum):
    legal = "legal"  # юридическое лицо
    ip = "ip"  # индивидуальный предприниматель


class CompanyStatus(StrEnum):
    active = "active"
    liquidating = "liquidating"
    liquidated = "liquidated"


class Purpose(StrEnum):
    working_capital = "working_capital"
    cash_gap = "cash_gap"
    equipment = "equipment"
    renovation = "renovation"
    refinancing = "refinancing"


class Collateral(StrEnum):
    real_estate = "real_estate"
    equipment = "equipment"
    none = "none"


class ApplicationStatus(StrEnum):
    draft = "draft"  # черновик, заполняется клиентом
    submitted = "submitted"  # подана, ждёт обработки
    validation = "validation"  # проверка полноты и корректности
    enrichment = "enrichment"  # запросы в БКИ, ЕГРЮЛ/ЕГРИП, «Прозрачный бизнес»
    scoring = "scoring"  # скоринговая оценка
    manual_review = "manual_review"  # рассматривает специалист банка
    docs_requested = "docs_requested"  # нужна дополнительная информация от клиента
    approved = "approved"  # одобрено на запрошенных условиях
    counter_offer = "counter_offer"  # одобрено на других условиях
    rejected = "rejected"  # отказ
    signing = "signing"  # подписание договора
    issued = "issued"  # кредит выдан
    declined_by_client = "declined_by_client"  # клиент отказался от предложения


# Группа статусов: заявка обрабатывается, фронт опрашивает сервер
PROCESSING_STATUSES = {
    ApplicationStatus.submitted,
    ApplicationStatus.validation,
    ApplicationStatus.enrichment,
    ApplicationStatus.scoring,
}

# Группа статусов: процесс завершен
TERMINAL_STATUSES = {
    ApplicationStatus.rejected,
    ApplicationStatus.issued,
    ApplicationStatus.declined_by_client,
}


class Actor(StrEnum):
    client = "client"
    system = "system"
    analyst = "analyst"


class CheckSource(StrEnum):
    bank = "bank"  # внутренние данные банка
    nbki = "nbki"  # бюро кредитных историй
    egrul = "egrul"  # ЕГРЮЛ / ЕГРИП
    pb = "pb"  # ФНС «Прозрачный бизнес»


class CheckStatus(StrEnum):
    ok = "ok"
    warning = "warning"
    fail = "fail"
    unavailable = "unavailable"


class Impact(StrEnum):
    positive = "positive"
    negative = "negative"
    neutral = "neutral"


class Weight(StrEnum):
    high = "high"
    medium = "medium"
    low = "low"


class DecisionOutcome(StrEnum):
    approved = "approved"
    counter_offer = "counter_offer"
    rejected = "rejected"
    docs_requested = "docs_requested"
    manual_review = "manual_review"


class DecidedBy(StrEnum):
    system = "system"
    analyst = "analyst"


class AnalystAction(StrEnum):
    approve = "approve"
    counter_offer = "counter_offer"
    request_docs = "request_docs"
    reject = "reject"


class OfferType(StrEnum):
    approved = "approved"
    counter_offer = "counter_offer"    


class InfoItemType(StrEnum):
    text = "text"
    number = "number"
