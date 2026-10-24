from fastapi import APIRouter

from app.schemas.enums import Collateral, InfoItemType, Purpose, RejectReason
from app.schemas.company import Company
from app.schemas.product import Product, RecommendRequest, RecommendResponse
from app.schemas.application import InfoRequestItem
from app.schemas.actions import Dictionaries, DictionaryItem
from app.errors import error_responses, not_found
from app.security import ClientUser
from app.services.assistant import recommend
from app.stubs.data import COMPANIES, PRODUCTS

router = APIRouter(tags=["Компания, продукты, справочники"])

PURPOSE_LABELS = {
    Purpose.working_capital: "Пополнение оборотных средств",
    Purpose.cash_gap: "Кассовый разрыв",
    Purpose.equipment: "Покупка оборудования",
    Purpose.renovation: "Ремонт и развитие",
    Purpose.refinancing: "Рефинансирование",
}
COLLATERAL_LABELS = {
    Collateral.real_estate: "Недвижимость",
    Collateral.equipment: "Оборудование",
    Collateral.none: "Без залога",
}
REJECT_REASON_LABELS = {
    RejectReason.debt_load: "Высокая долговая нагрузка",
    RejectReason.credit_history: "Негативная кредитная история",
    RejectReason.company_inactive: "Компания не действует",
    RejectReason.insufficient_data: "Недостаточно данных для оценки",
    RejectReason.risk_signals: "Признаки повышенного риска",
    RejectReason.other: "Другая причина",
}
INFO_ITEMS = [
    InfoRequestItem(code="monthly_revenue_confirm", label="Среднемесячная выручка за 6 месяцев, ₽", type=InfoItemType.number),
    InfoRequestItem(code="main_bank", label="Банк, где ведутся основные обороты", type=InfoItemType.text),
    InfoRequestItem(code="purpose_details", label="Подробнее о цели кредита", type=InfoItemType.text),
    InfoRequestItem(code="actual_address", label="Фактический адрес ведения бизнеса", type=InfoItemType.text),
]


@router.get(
    "/me/company",
    response_model=Company,
    summary="Компания текущего клиента",
    description="Реквизиты известны банку заранее - клиент их не вводит.",
    responses=error_responses(401, 403, 404),
)
def my_company(user: ClientUser) -> Company:
    company = COMPANIES.get(user.inn or "")
    if company is None:
        raise not_found("company", "Компания не найдена")
    return company


@router.get("/products", response_model=list[Product], summary="Каталог кредитных продуктов")
def products() -> list[Product]:
    return PRODUCTS


@router.post(
    "/assistant/recommend",
    response_model=RecommendResponse,
    summary="Подбор продукта по цели, сумме и сроку",
    description="Правила подбора без ИИ: порядок зависит от цели, продукты вне лимитов по сумме отсеиваются.",
    responses=error_responses(422),
)
def assistant_recommend(body: RecommendRequest) -> RecommendResponse:
    return recommend(body, PRODUCTS)


@router.get("/dictionaries", response_model=Dictionaries, summary="Справочники")
def dictionaries() -> Dictionaries:
    return Dictionaries(
        purposes=[DictionaryItem(code=k.value, label=v) for k, v in PURPOSE_LABELS.items()],
        collateral_types=[DictionaryItem(code=k.value, label=v) for k, v in COLLATERAL_LABELS.items()],
        reject_reasons=[DictionaryItem(code=k.value, label=v) for k, v in REJECT_REASON_LABELS.items()],
        info_items=INFO_ITEMS,
    )
