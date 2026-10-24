"""Финансовые расчеты, общие для скоринга, оффера и подбора продукта."""

KEY_RATE = 14.0  # ключевая ставка, % (допущение, подробнее см. README)


def annuity_payment(amount: int, rate_percent: float, term_months: int) -> int:
    """Ежемесячный аннуитетный платеж, округленный до рубля."""
    if term_months <= 0:
        raise ValueError("term_months must be positive")
    monthly_rate = rate_percent / 100 / 12
    if monthly_rate == 0:
        return round(amount / term_months)
    payment = amount * monthly_rate / (1 - (1 + monthly_rate) ** -term_months)
    return round(payment)
