"""Синтетические реквизиты должны проходить проверку контрольных сумм. БД не нужна"""

import pytest

from app.config import get_settings
from app.services.requisites import is_valid_account, is_valid_inn, is_valid_ogrn
from app.db.seed import BANK_BIK, SeedCompany, read_seed

COMPANIES = read_seed("companies.json", SeedCompany, get_settings().seed_dir)


@pytest.mark.parametrize("company", COMPANIES, ids=lambda c: c.name)
def test_company_requisites_are_valid(company: SeedCompany) -> None:
    assert is_valid_inn(company.inn)
    assert is_valid_ogrn(company.ogrn)
    assert is_valid_account(company.account, BANK_BIK)


def test_invalid_values_are_rejected() -> None:
    assert not is_valid_inn("1655482319")  # изменена последняя цифра
    assert not is_valid_ogrn("1241600057127")
    assert not is_valid_inn("12345")
