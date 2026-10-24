"""Синтетические реквизиты должны проходить проверку контрольных сумм."""

import pytest

from app.services.requisites import is_valid_account, is_valid_inn, is_valid_ogrn
from app.stubs.data import BANK_BIK, COMPANIES


@pytest.mark.parametrize("company", COMPANIES.values(), ids=lambda c: c.name)
def test_company_requisites_are_valid(company) -> None:
    assert is_valid_inn(company.inn)
    assert is_valid_ogrn(company.ogrn)
    assert is_valid_account(company.account, BANK_BIK)


def test_invalid_values_are_rejected() -> None:
    assert not is_valid_inn("1655482319")  # изменена последняя цифра
    assert not is_valid_ogrn("1241600057127")
    assert not is_valid_inn("12345")
