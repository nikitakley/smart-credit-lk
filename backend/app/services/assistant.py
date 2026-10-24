"""Помощник подбора продукта: правила без ИИ.

Порядок продуктов зависит от цели финансирования. 
Продукты, у которых сумма вне лимитов, отсеиваются; 
если не подходит только срок - продукт остаётся с оговоркой.
"""

from app.schemas.enums import Collateral, Purpose
from app.schemas.product import Product, RecommendItem, RecommendRequest, RecommendResponse

PURPOSE_PRIORITY: dict[Purpose, list[str]] = {
    Purpose.working_capital: ["working-capital", "overdraft", "investment"],
    Purpose.cash_gap: ["overdraft", "working-capital", "investment"],
    Purpose.equipment: ["investment", "working-capital", "overdraft"],
    Purpose.renovation: ["investment", "working-capital", "overdraft"],
    Purpose.refinancing: ["working-capital", "investment", "overdraft"],
}

PURPOSE_REASON: dict[str, dict[Purpose, str]] = {
    "working-capital": {
        Purpose.working_capital: "Создан для пополнения оборотных средств",
        Purpose.refinancing: "Подходит для рефинансирования текущих обязательств",
    },
    "overdraft": {
        Purpose.cash_gap: "Закрывает кассовые разрывы: деньги доступны сразу, проценты - только за использованную сумму",
        Purpose.working_capital: "Удобен для коротких потребностей в оборотке",
    },
    "investment": {
        Purpose.equipment: "Рассчитан на покупку оборудования и длинный срок окупаемости",
        Purpose.renovation: "Рассчитан на ремонт и развитие с длинным сроком",
    },
}

PURPOSE_LABEL = {
    Purpose.working_capital: "пополнение оборотных средств",
    Purpose.cash_gap: "кассовый разрыв",
    Purpose.equipment: "покупку оборудования",
    Purpose.renovation: "ремонт и развитие",
    Purpose.refinancing: "рефинансирование",
}


def _fmt_money(value: int) -> str:
    return f"{value:,}".replace(",", " ") + " ₽"


def recommend(request: RecommendRequest, products: list[Product]) -> RecommendResponse:
    by_id = {p.id: p for p in products}
    order = PURPOSE_PRIORITY.get(request.purpose, list(by_id))

    items: list[RecommendItem] = []
    for product_id in order:
        product = by_id.get(product_id)
        if product is None:
            continue
        if not (product.min_amount <= request.amount <= product.max_amount):
            continue

        reasons: list[str] = []
        if purpose_reason := PURPOSE_REASON.get(product.id, {}).get(request.purpose):
            reasons.append(purpose_reason)
        reasons.append(
            f"Сумма {_fmt_money(request.amount)} в пределах лимита "
            f"{_fmt_money(product.min_amount)} – {_fmt_money(product.max_amount)}"
        )
        reasons.append(f"Ставка от {product.rate_from}% годовых")
        if request.collateral != Collateral.none:
            reasons.append("Залог может снизить ставку и увеличить доступную сумму")

        caveat = None
        if request.term_months > product.max_term_months:
            caveat = f"Максимальный срок - {product.max_term_months} мес., срок будет уменьшен"

        items.append(RecommendItem(product=product, best=False, reasons=reasons, caveat=caveat))

    # Лучший продукт: первый по приоритету без оговорок (caveat), иначе просто первый
    best = next((i for i in items if i.caveat is None), items[0] if items else None)
    if best is not None:
        best.best = True

    if items:
        summary = (
            f"Для цели «{PURPOSE_LABEL[request.purpose]}» на {_fmt_money(request.amount)} "
            f"подходит продуктов: {len(items)}. Рекомендуем «{best.product.name}»."
        )
    else:
        summary = (
            f"Под сумму {_fmt_money(request.amount)} нет подходящих продуктов. "
            "Попробуйте изменить сумму - специалист банка поможет подобрать вариант."
        )
    return RecommendResponse(summary=summary, items=items)
