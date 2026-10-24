"""Проверка реквизитов по контрольным суммам: ИНН, ОГРН/ОГРНИП, расчетный счет.

Используется для проверки корректности данных на этапе validation
и для генерации правдоподобных синтетических реквизитов.
"""

INN10_WEIGHTS = (2, 4, 10, 3, 5, 9, 4, 6, 8)
INN12_WEIGHTS_1 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
INN12_WEIGHTS_2 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
ACCOUNT_WEIGHTS = (7, 1, 3) * 7 + (7, 1)


def _check_digit(digits: str, weights: tuple[int, ...]) -> int:
    return sum(int(d) * w for d, w in zip(digits, weights)) % 11 % 10


def is_valid_inn(inn: str) -> bool:
    """ИНН юрлица - 10 цифр, ИНН физлица/ИП - 12 цифр."""
    if not inn.isdigit():
        return False
    if len(inn) == 10:
        return _check_digit(inn[:9], INN10_WEIGHTS) == int(inn[9])
    if len(inn) == 12:
        return (_check_digit(inn[:10], INN12_WEIGHTS_1) == int(inn[10]) 
                and _check_digit(inn[:11], INN12_WEIGHTS_2) == int(inn[11]))
    return False


def is_valid_ogrn(ogrn: str) -> bool:
    """ОГРН юрлица - 13 цифр, ОГРНИП - 15 цифр."""
    if not ogrn.isdigit():
        return False
    if len(ogrn) == 13:
        return int(ogrn[:12]) % 11 % 10 == int(ogrn[12])
    if len(ogrn) == 15:
        return int(ogrn[:14]) % 13 % 10 == int(ogrn[14])
    return False    


def is_valid_account(account: str, bik: str) -> bool:
    """Расчетный счет (20 цифр) с контрольным ключом по БИК банка."""
    if not (account.isdigit() and len(account) == 20 and bik.isdigit() and len(bik) == 9):
        return False
    payload = bik[-3:] + account
    return sum(int(d) * w for d, w in zip(payload, ACCOUNT_WEIGHTS)) % 10 == 0    


# --- [Генерация для синтетических данных и тестов]


def make_inn10(first9: str) -> str:
    return first9 + str(_check_digit(first9, INN10_WEIGHTS))


def make_inn12(first10: str) -> str:
    d11 = str(_check_digit(first10, INN12_WEIGHTS_1))
    d12 = str(_check_digit(first10 + d11, INN12_WEIGHTS_2))
    return first10 + d11 + d12


def make_ogrn(first12: str) -> str:
    return first12 + str(int(first12) % 11 % 10)


def make_ogrnip(first14: str) -> str:
    return first14 + str(int(first14) % 13 % 10)


def make_account(prefix8: str, number11: str, bik: str) -> str:
    """Расчетный счет: 5 цифр балансового счета + 3 цифры валюты + ключ + 11 цифр номера."""
    for key in range(10):
        account = f"{prefix8}{key}{number11}"
        if is_valid_account(account, bik):
            return account
    raise ValueError("cannot build account")
