"""Форматирование чисел для текстов, которые читает человек."""


def rub(amount: int) -> str:
    """1500000 → «1 500 000 ₽»."""
    return f"{amount:,}".replace(",", " ") + " ₽"


def plural(n: int, forms: tuple[str, str, str]) -> str:
    """Форма слова для числа: plural(4, ("месяц", "месяца", "месяцев")) → «месяца»."""
    n = abs(n)
    if n % 10 == 1 and n % 100 != 11:
        return forms[0]
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return forms[1]
    return forms[2]
