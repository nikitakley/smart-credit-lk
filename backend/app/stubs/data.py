"""ВРЕМЕННЫЕ демо-данные для заглушек этапа 1.

На этапе 2 их заменят сиды в БД (data/seed). Все данные синтетические.
Заявки собраны так, чтобы фронтенд мог проверить каждый экран:
    A-1020  ООО «Продмаркет»        draft           — черновик
    A-1021  ООО «Уралстройинвест»   rejected        — отказ (компания ликвидирована)
    A-1022  ООО «Вектор Софт»       approved        — одобрено, оффер на запрошенных условиях
    A-1023  ИП Сидоров П. А.        docs_requested  — банк запросил информацию
    A-1024  ООО «Продмаркет»        counter_offer   — контрпредложение
    A-1025  ООО «СибТоргКомплект»   manual_review   — на ручной проверке у аналитика
    A-1026  ООО «Вектор Софт»       enrichment      — в обработке (запросы во внешние источники)
"""

from datetime import date, datetime, timedelta, timezone

from app.schemas.application import (
    ApplicationAnalyst,
    CheckDetailed,
    Contact,
    Decision,
    Explanation,
    HistoryEvent,
    InfoRequest,
    InfoRequestItem,
    Offer,
    OfferRequested,
    RateBreakdown,
    Score,
    ScoredFactor,
    ScoringInputs,
    SystemRecommendation,
)
from app.schemas.auth import TestAccount
from app.schemas.company import Company, Founder, Okved
from app.schemas.enums import (
    Actor,
    ApplicationStatus as S,
    CheckSource,
    CheckStatus,
    Collateral,
    CompanyStatus,
    CompanyType,
    DecidedBy,
    DecisionOutcome,
    Impact,
    InfoItemType,
    OfferType,
    Purpose,
    Role,
    Weight,
)
from app.schemas.product import Product
from app.services.finance import KEY_RATE, annuity_payment

MSK = timezone(timedelta(hours=3))


def _now() -> datetime:
    return datetime.now(MSK).replace(microsecond=0)


def _product(pid: str, name: str, note: str, min_a: int, max_a: int, term: int, spread: float) -> Product:
    return Product(
        id=pid,
        name=name,
        note=note,
        min_amount=min_a,
        max_amount=max_a,
        max_term_months=term,
        spread=spread,
        rate_from=round(KEY_RATE + spread, 2),
    )


PRODUCTS: list[Product] = [
    _product("working-capital", "Оборотный кредит", "Пополнение оборотных средств", 300_000, 10_000_000, 36, 4.5),
    _product("investment", "Кредит на развитие", "Оборудование, ремонт, развитие бизнеса", 1_000_000, 30_000_000, 60, 3.9),
    _product("overdraft", "Овердрафт", "Кассовые разрывы, деньги доступны сразу", 100_000, 5_000_000, 12, 5.5),
]
PRODUCTS_BY_ID = {p.id: p for p in PRODUCTS}


# БИК банка — для контрольного ключа расчётных счетов
BANK_BIK = "044525593"

FETCHED_AT = datetime(2026, 10, 20, 10, 12, tzinfo=MSK)

# Реквизиты синтетические, но корректны по контрольным суммам (см. app/services/requisites.py).
# Телефоны с номером на 000 не выдаются абонентам, почта — на зарезервированном домене .example.
COMPANIES: dict[str, Company] = {
    c.inn: c
    for c in [
        # Продуктовый ритейл, 2 года, растущая выручка, но высокая долговая нагрузка → контрпредложение
        Company(
            inn="1655482318", type=CompanyType.legal, status=CompanyStatus.active,
            name="ООО «Продмаркет»",
            full_name="Общество с ограниченной ответственностью «Продмаркет»",
            ogrn="1241600057126", kpp="165501001", registered_at=date(2024, 6, 11),
            director="Гарипов Рустам Ильдарович", director_title="Генеральный директор",
            founders=[Founder(name="Гарипов Рустам Ильдарович", share_percent=60),
                      Founder(name="Сафина Алсу Ринатовна", share_percent=40)],
            okved=Okved(code="47.11", title="Торговля розничная преимущественно пищевыми продуктами "
                                           "в неспециализированных магазинах"),
            legal_address="420107, Республика Татарстан, г. Казань, ул. Спартаковская, д. 88, пом. 14",
            phone="+7 (843) 000-27-14", email="finance@prodmarket.example",
            account="40702810562000014827", fetched_at=FETCHED_AT,
        ),
        # Разработка ПО, 8 лет, стабильный рост → одобрение
        Company(
            inn="7810624578", type=CompanyType.legal, status=CompanyStatus.active,
            name="ООО «Вектор Софт»",
            full_name="Общество с ограниченной ответственностью «Вектор Софт»",
            ogrn="1187847036519", kpp="781001001", registered_at=date(2018, 3, 5),
            director="Белова Анна Сергеевна", director_title="Генеральный директор",
            founders=[Founder(name="Белова Анна Сергеевна", share_percent=51),
                      Founder(name="Орлов Максим Викторович", share_percent=49)],
            okved=Okved(code="62.01", title="Разработка компьютерного программного обеспечения"),
            legal_address="196084, г. Санкт-Петербург, Московский пр-кт, д. 97, лит. А, оф. 412",
            phone="+7 (812) 000-41-90", email="cfo@vektorsoft.example",
            account="40702810632000003195", fetched_at=FETCHED_AT,
        ),
        # Кафе, ИП меньше 2 лет, счёт в банке открыт недавно → запрос информации
        Company(
            inn="504718329642", type=CompanyType.ip, status=CompanyStatus.active,
            name="ИП Сидоров Пётр Алексеевич",
            full_name="Индивидуальный предприниматель Сидоров Пётр Алексеевич",
            ogrn="325500000128746", kpp=None, registered_at=date(2025, 2, 17),
            director="Сидоров Пётр Алексеевич", director_title="Индивидуальный предприниматель",
            founders=[],
            okved=Okved(code="56.10", title="Деятельность ресторанов и услуги по доставке продуктов питания"),
            legal_address="141407, Московская обл., г. Химки, ул. Московская, д. 21, кв. 56",
            phone="+7 (495) 000-63-18", email="sidorov.cafe@mail.example",
            account="40802810840000008361", fetched_at=FETCHED_AT,
        ),
        # Строительство, компания ликвидирована → отказ (стоп-фактор)
        Company(
            inn="6671034827", type=CompanyType.legal, status=CompanyStatus.liquidated,
            name="ООО «Уралстройинвест»",
            full_name="Общество с ограниченной ответственностью «Уралстройинвест»",
            ogrn="1156674012384", kpp="667101001", registered_at=date(2015, 9, 1),
            director="Кузнецов Олег Викторович", director_title="Ликвидатор",
            founders=[Founder(name="Кузнецов Олег Викторович", share_percent=100)],
            okved=Okved(code="41.20", title="Строительство жилых и нежилых зданий"),
            legal_address="620075, Свердловская обл., г. Екатеринбург, ул. Малышева, д. 51, оф. 1203",
            phone="+7 (343) 000-75-02", email="office@uralstroyinvest.example",
            account="40702810616000002549", fetched_at=FETCHED_AT,
        ),
        # Оптовая торговля, массовый адрес регистрации → ручная проверка
        Company(
            inn="5406247181", type=CompanyType.legal, status=CompanyStatus.active,
            name="ООО «СибТоргКомплект»",
            full_name="Общество с ограниченной ответственностью «СибТоргКомплект»",
            ogrn="1215400015379", kpp="540601001", registered_at=date(2021, 11, 23),
            director="Морозов Дмитрий Андреевич", director_title="Генеральный директор",
            founders=[Founder(name="Морозов Дмитрий Андреевич", share_percent=100)],
            okved=Okved(code="46.90", title="Торговля оптовая неспециализированная"),
            legal_address="630099, Новосибирская обл., г. Новосибирск, ул. Советская, д. 5, оф. 301",
            phone="+7 (383) 000-58-46", email="buh@sibtorgkomplekt.example",
            account="40702810144000009713", fetched_at=FETCHED_AT,
        ),
    ]
}

TEST_ACCOUNTS: list[TestAccount] = [
    TestAccount(id="prodmarket", role=Role.client, inn="1655482318", name="ООО «Продмаркет»",
                hint="Контрпредложение банка — примите его и пройдите до выдачи"),
    TestAccount(id="vektor", role=Role.client, inn="7810624578", name="ООО «Вектор Софт»",
                hint="Одобрено на запрошенных условиях; вторая заявка в обработке"),
    TestAccount(id="sidorov", role=Role.client, inn="504718329642", name="ИП Сидоров П. А.",
                hint="Банк запросил дополнительную информацию"),
    TestAccount(id="sibtorg", role=Role.client, inn="5406247181", name="ООО «СибТоргКомплект»",
                hint="Заявка на ручной проверке у специалиста"),
    TestAccount(id="uralstroy", role=Role.client, inn="6671034827", name="ООО «Уралстройинвест»",
                hint="Отказ: компания ликвидирована"),
    TestAccount(id="analyst", role=Role.analyst, inn=None, name="Смирнова Елена, кредитный аналитик",
                hint="Очередь заявок и решения по спорным случаям"),
]


def _contact(company: Company) -> Contact:
    return Contact(name=company.director, phone=company.phone, email=company.email)


def _checks(now: datetime, *, egrul: CheckStatus = CheckStatus.ok, egrul_text: str = "Компания действует",
            pb: CheckStatus = CheckStatus.ok, pb_text: str = "Признаков риска не выявлено",
            nbki_text: str = "Просрочек за 24 месяца нет", bank_text: str = "Обороты по счёту стабильны") -> list[CheckDetailed]:
    return [
        CheckDetailed(source=CheckSource.bank, title="Обороты по счёту в банке", status=CheckStatus.ok,
                      summary=bank_text, fetched_at=now, details={}),
        CheckDetailed(source=CheckSource.egrul, title="ЕГРЮЛ / ЕГРИП", status=egrul,
                      summary=egrul_text, fetched_at=now, details={}),
        CheckDetailed(source=CheckSource.pb, title="ФНС «Прозрачный бизнес»", status=pb,
                      summary=pb_text, fetched_at=now, details={}),
        CheckDetailed(source=CheckSource.nbki, title="Бюро кредитных историй", status=CheckStatus.ok,
                      summary=nbki_text, fetched_at=now, details={}),
    ]


def _pipeline_history(start: datetime) -> list[HistoryEvent]:
    return [
        HistoryEvent(status=S.submitted, at=start, actor=Actor.client, note="Заявка отправлена в банк"),
        HistoryEvent(status=S.validation, at=start + timedelta(seconds=5), actor=Actor.system,
                     note="Проверяем полноту и корректность данных"),
        HistoryEvent(status=S.enrichment, at=start + timedelta(seconds=10), actor=Actor.system,
                     note="Запрашиваем данные в БКИ, ЕГРЮЛ и «Прозрачном бизнесе»"),
        HistoryEvent(status=S.scoring, at=start + timedelta(seconds=20), actor=Actor.system,
                     note="Оцениваем финансовое положение"),
    ]


def _rate(product: Product, risk_premium: float) -> RateBreakdown:
    return RateBreakdown(key_rate=KEY_RATE, product_spread=product.spread, risk_premium=risk_premium,
                         rate=round(KEY_RATE + product.spread + risk_premium, 2))


def _offer(now: datetime, otype: OfferType, product: Product, amount: int, term: int, risk: float,
           requested: tuple[int, int, Collateral]) -> Offer:
    rb = _rate(product, risk)
    return Offer(
        type=otype, amount=amount, term_months=term, rate=rb.rate, rate_breakdown=rb,
        monthly_payment=annuity_payment(amount, rb.rate, term), collateral_required=Collateral.none,
        valid_until=now + timedelta(days=7),
        requested=OfferRequested(amount=requested[0], term_months=requested[1], collateral=requested[2]),
    )


def build_applications() -> dict[str, ApplicationAnalyst]:
    now = _now()
    wc, inv, ovd = PRODUCTS_BY_ID["working-capital"], PRODUCTS_BY_ID["investment"], PRODUCTS_BY_ID["overdraft"]
    prodmarket, vektor, sidorov = COMPANIES["1655482318"], COMPANIES["7810624578"], COMPANIES["504718329642"]
    uralstroy, sibtorg = COMPANIES["6671034827"], COMPANIES["5406247181"]
    apps: list[ApplicationAnalyst] = []

    # A-1020 — черновик
    t = now - timedelta(minutes=30)
    apps.append(ApplicationAnalyst(
        id="A-1020", company=prodmarket, product_id=ovd.id, product_name=ovd.name, amount=500_000, term_months=6,
        purpose=Purpose.cash_gap, collateral=Collateral.none, contact=_contact(prodmarket),
        status=S.draft, created_at=t, updated_at=t,
    ))

    # A-1021 — отказ: компания ликвидирована (стоп-фактор ЕГРЮЛ)
    t = now - timedelta(days=3)
    apps.append(ApplicationAnalyst(
        id="A-1021", company=uralstroy, product_id=wc.id, product_name=wc.name, amount=3_000_000, term_months=24,
        purpose=Purpose.working_capital, collateral=Collateral.none, contact=_contact(uralstroy),
        status=S.rejected, created_at=t, updated_at=t + timedelta(minutes=1), submitted_at=t,
        history=_pipeline_history(t)[:3] + [
            HistoryEvent(status=S.rejected, at=t + timedelta(seconds=15), actor=Actor.system,
                         note="По данным ЕГРЮЛ компания ликвидирована"),
        ],
        checks=_checks(t, egrul=CheckStatus.fail, egrul_text="Компания ликвидирована"),
        factors=[ScoredFactor(code="company_status", label="Компания ликвидирована",
                              detail="По данным ЕГРЮЛ деятельность прекращена", impact=Impact.negative,
                              weight=Weight.high, points=-1000)],
        decision=Decision(outcome=DecisionOutcome.rejected, requested_amount=3_000_000, decided_by=DecidedBy.system,
                          decided_at=t + timedelta(seconds=15), reason_code="company_inactive",
                          comment_for_client="Банк не может выдать кредит: по данным ЕГРЮЛ компания ликвидирована",
                          followed_system=True),
        explanation=Explanation(text="Кредит выдаётся только действующим компаниям. По данным ЕГРЮЛ "
                                     "деятельность ООО «Уралстройинвест» прекращена.", generated_at=t + timedelta(seconds=15)),
        system_recommendation=SystemRecommendation(outcome=DecisionOutcome.rejected,
                                                   text="Отказ: стоп-фактор — компания ликвидирована"),
    ))

    # A-1022 — одобрено на запрошенных условиях
    t = now - timedelta(days=1, hours=2)
    apps.append(ApplicationAnalyst(
        id="A-1022", company=vektor, product_id=inv.id, product_name=inv.name, amount=5_000_000, term_months=36,
        purpose=Purpose.equipment, collateral=Collateral.none, contact=_contact(vektor),
        status=S.approved, created_at=t, updated_at=t + timedelta(minutes=1), submitted_at=t,
        history=_pipeline_history(t) + [
            HistoryEvent(status=S.approved, at=t + timedelta(seconds=30), actor=Actor.system,
                         note="Одобрено на запрошенных условиях"),
        ],
        checks=_checks(t, bank_text="Выручка за 12 месяцев выросла на 25%"),
        factors=[
            ScoredFactor(code="revenue_trend", label="Растущая выручка", detail="Выручка за 12 месяцев выросла на 25%",
                         impact=Impact.positive, weight=Weight.high, points=120),
            ScoredFactor(code="debt_load", label="Низкая долговая нагрузка",
                         detail="Платежи по кредитам с новым займом — 22% выручки (лимит 50%)",
                         impact=Impact.positive, weight=Weight.medium, points=60),
            ScoredFactor(code="credit_history", label="Нет просрочек", detail="Кредитная история без просрочек за 2 года",
                         impact=Impact.positive, weight=Weight.medium, points=80),
            ScoredFactor(code="business_age", label="Бизнес работает больше 5 лет", detail="8 лет 7 месяцев",
                         impact=Impact.positive, weight=Weight.medium, points=60),
        ],
        score=Score(value=880, max=1000, min_score=450),
        scoring_inputs=ScoringInputs(monthly_revenue=4_200_000, revenue_growth=25, loan_payments=750_000,
                                     overdues_24m=0, age_months=103, dti_now=18, dti_with_requested=22,
                                     affordable=20_000_000),
        rate_breakdown=_rate(inv, 0),
        system_recommendation=SystemRecommendation(outcome=DecisionOutcome.approved, amount=5_000_000, term_months=36,
                                                   rate=_rate(inv, 0).rate, text="Одобрить на запрошенных условиях"),
        decision=Decision(outcome=DecisionOutcome.approved, requested_amount=5_000_000, approved_amount=5_000_000,
                          decided_by=DecidedBy.system, decided_at=t + timedelta(seconds=30), followed_system=True),
        explanation=Explanation(text="Выручка растёт, долговая нагрузка низкая, просрочек нет — банк одобрил "
                                     "кредит на запрошенных условиях.", generated_at=t + timedelta(seconds=30)),
        offer=_offer(now, OfferType.approved, inv, 5_000_000, 36, 0, (5_000_000, 36, Collateral.none)),
    ))

    # A-1023 — запрос дополнительной информации
    t = now - timedelta(hours=5)
    apps.append(ApplicationAnalyst(
        id="A-1023", company=sidorov, product_id=wc.id, product_name=wc.name, amount=1_500_000, term_months=18,
        purpose=Purpose.working_capital, collateral=Collateral.none, contact=_contact(sidorov),
        status=S.docs_requested, created_at=t, updated_at=t + timedelta(minutes=1), submitted_at=t,
        history=_pipeline_history(t) + [
            HistoryEvent(status=S.docs_requested, at=t + timedelta(seconds=30), actor=Actor.system,
                         note="Счёт в банке открыт недавно — подтвердите выручку"),
        ],
        checks=_checks(t, bank_text="Обороты по счёту только за 4 месяца — недостаточно для оценки"),
        info_request=InfoRequest(
            requested_at=t + timedelta(seconds=30),
            comment="Счёт в нашем банке открыт недавно, оборотов недостаточно для оценки. Укажите выручку "
                    "за последние 6 месяцев и банк, где ведутся основные обороты.",
            items=[
                InfoRequestItem(code="monthly_revenue_confirm", label="Среднемесячная выручка за 6 месяцев, ₽",
                                type=InfoItemType.number),
                InfoRequestItem(code="main_bank", label="Банк, где ведутся основные обороты", type=InfoItemType.text),
            ],
        ),
        system_recommendation=SystemRecommendation(outcome=DecisionOutcome.docs_requested,
                                                   text="Недостаточно данных о выручке — запросить подтверждение"),
    ))

    # A-1024 — контрпредложение (пример из фронтенда)
    t = now - timedelta(hours=2)
    rb = _rate(wc, 1)
    apps.append(ApplicationAnalyst(
        id="A-1024", company=prodmarket, product_id=wc.id, product_name=wc.name, amount=2_000_000, term_months=24,
        purpose=Purpose.working_capital, collateral=Collateral.none, contact=_contact(prodmarket),
        status=S.counter_offer, created_at=t, updated_at=t + timedelta(minutes=1), submitted_at=t,
        history=_pipeline_history(t) + [
            HistoryEvent(status=S.counter_offer, at=t + timedelta(seconds=30), actor=Actor.system,
                         note="Сумма снижена из-за долговой нагрузки"),
        ],
        checks=_checks(t, bank_text="Выручка за 12 месяцев выросла на 18%",
                       nbki_text="Просрочек нет, платежи по кредитам — 720 000 ₽ в месяц"),
        factors=[
            ScoredFactor(code="revenue_trend", label="Растущая выручка", detail="Выручка за 12 месяцев выросла на 18%",
                         impact=Impact.positive, weight=Weight.high, points=120),
            ScoredFactor(code="debt_load", label="Высокая долговая нагрузка",
                         detail="Платежи по текущим кредитам — 45% выручки (лимит 50%)",
                         impact=Impact.negative, weight=Weight.medium, points=-80),
            ScoredFactor(code="credit_history", label="Нет просрочек", detail="Кредитная история без просрочек за 2 года",
                         impact=Impact.positive, weight=Weight.medium, points=80),
            ScoredFactor(code="business_age", label="Срок работы бизнеса", detail="2 года 4 месяца",
                         impact=Impact.neutral, weight=Weight.low, points=0),
        ],
        score=Score(value=680, max=1000, min_score=450),
        scoring_inputs=ScoringInputs(monthly_revenue=1_600_000, revenue_growth=18, loan_payments=720_000,
                                     overdues_24m=0, age_months=28, dti_now=45, dti_with_requested=51,
                                     affordable=1_500_000),
        rate_breakdown=rb,
        system_recommendation=SystemRecommendation(
            outcome=DecisionOutcome.counter_offer, amount=1_500_000, term_months=24, rate=rb.rate,
            text="Контрпредложение: 1 500 000 ₽ вместо 2 000 000 ₽. С запрошенной суммой платежи по кредитам "
                 "заняли бы 51% выручки при лимите 50%."),
        decision=Decision(outcome=DecisionOutcome.counter_offer, requested_amount=2_000_000, approved_amount=1_500_000,
                          decided_by=DecidedBy.system, decided_at=t + timedelta(seconds=30),
                          comment_for_client="Сумма снижена из-за долговой нагрузки", followed_system=True),
        explanation=Explanation(
            text="Сумму снизили до 1 500 000 ₽: с 2 000 000 ₽ платежи по всем кредитам заняли бы 51% выручки "
                 "при лимите 50%. Выручка растёт и просрочек нет, поэтому банк готов выдать кредит на меньшую сумму.",
            generated_at=t + timedelta(seconds=30)),
        improvements=["Погасить часть текущих кредитов: лимит нагрузки — 50% выручки",
                      "Добавить залог или поручительство",
                      "Перевести обороты на счёт в банке — банк увидит выручку точнее"],
        offer=_offer(now, OfferType.counter_offer, wc, 1_500_000, 24, 1, (2_000_000, 24, Collateral.none)),
    ))

    # A-1025 — ручная проверка: массовый адрес по данным «Прозрачного бизнеса»
    t = now - timedelta(hours=1)
    apps.append(ApplicationAnalyst(
        id="A-1025", company=sibtorg, product_id=wc.id, product_name=wc.name, amount=4_000_000, term_months=24,
        purpose=Purpose.working_capital, collateral=Collateral.none, contact=_contact(sibtorg),
        status=S.manual_review, created_at=t, updated_at=t + timedelta(minutes=1), submitted_at=t,
        history=_pipeline_history(t) + [
            HistoryEvent(status=S.manual_review, at=t + timedelta(seconds=30), actor=Actor.system,
                         note="Заявку рассматривает специалист банка"),
        ],
        checks=_checks(t, pb=CheckStatus.warning, pb_text="Адрес регистрации указан у 54 компаний (массовый адрес)"),
        factors=[
            ScoredFactor(code="mass_address", label="Массовый адрес регистрации",
                         detail="По этому адресу зарегистрированы 54 компании", impact=Impact.negative,
                         weight=Weight.high, points=-100),
            ScoredFactor(code="debt_load", label="Умеренная долговая нагрузка",
                         detail="Платежи по кредитам с новым займом — 38% выручки (лимит 50%)",
                         impact=Impact.neutral, weight=Weight.low, points=0),
            ScoredFactor(code="credit_history", label="Нет просрочек", detail="Кредитная история без просрочек за 2 года",
                         impact=Impact.positive, weight=Weight.medium, points=80),
        ],
        score=Score(value=540, max=1000, min_score=450),
        scoring_inputs=ScoringInputs(monthly_revenue=2_800_000, revenue_growth=4, loan_payments=860_000,
                                     overdues_24m=0, age_months=59, dti_now=31, dti_with_requested=38,
                                     affordable=5_500_000),
        rate_breakdown=_rate(wc, 2.5),
        system_recommendation=SystemRecommendation(
            outcome=DecisionOutcome.manual_review, amount=4_000_000, term_months=24, rate=_rate(wc, 2.5).rate,
            text="Финансовые показатели позволяют одобрить, но есть признак риска — массовый адрес. "
                 "Нужна проверка специалистом."),
    ))

    # A-1026 — в обработке: идёт обогащение данными
    t = now - timedelta(seconds=40)
    apps.append(ApplicationAnalyst(
        id="A-1026", company=vektor, product_id=ovd.id, product_name=ovd.name, amount=1_000_000, term_months=12,
        purpose=Purpose.cash_gap, collateral=Collateral.none, contact=_contact(vektor),
        status=S.enrichment, created_at=t, updated_at=t + timedelta(seconds=10), submitted_at=t,
        history=_pipeline_history(t)[:3],
        checks=_checks(t)[:2],
    ))

    return {a.id: a for a in apps}
