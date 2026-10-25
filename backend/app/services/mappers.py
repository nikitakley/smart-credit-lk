"""Преобразование ORM-моделей (как данные хранятся) в схемы API (как их видит клиент)."""

from app.schemas.company import Company, Founder, Okved
from app.schemas.product import Product
from app.services.finance import KEY_RATE
from app.db import models


def product_to_schema(product: models.Product) -> Product:
    spread = float(product.spread)
    return Product(
        id=product.id,
        name=product.name,
        note=product.note,
        min_amount=product.min_amount,
        max_amount=product.max_amount,
        max_term_months=product.max_term_months,
        spread=spread,
        rate_from=round(KEY_RATE + spread, 2),  # в базе не хранится
    )


def company_to_schema(company: models.Company) -> Company:
    return Company(
        inn=company.inn,
        type=company.type,
        status=company.status,
        name=company.name,
        full_name=company.full_name,
        ogrn=company.ogrn,
        kpp=company.kpp,
        registered_at=company.registered_at,
        director=company.director,
        director_title=company.director_title,
        founders=[Founder.model_validate(f) for f in company.founders],
        okved=Okved(code=company.okved_code, title=company.okved_title),
        legal_address=company.legal_address,
        phone=company.phone,
        email=company.email,
        account=company.account,
        source=company.source,
        fetched_at=company.fetched_at,
    )