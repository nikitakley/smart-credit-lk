from pydantic import Field

from app.schemas.base import CamelModel
from app.schemas.enums import Collateral, Purpose


class Product(CamelModel):
    id: str = Field(examples=["working-capital"])
    name: str = Field(examples=["Оборотный кредит"])
    note: str = Field(examples=["Пополнение оборотных средств"])
    min_amount: int = Field(description="Минимальная сумма, ₽", examples=[300000])
    max_amount: int = Field(description="Максимальная сумма, ₽", examples=[10000000])
    max_term_monts: int = Field(examples=[36])
    spread: float = Field(description="Спред продукта к ключевой ставке, п.п.", examples=[4.5])
    rate_from: float = Field(description="Ставка от, % годовых", examples=[18.5])


class RecommendRequest(CamelModel):
    purpose: Purpose
    amount: int = Field(gt=0, description="Ориентировочная сумма, ₽")
    term_months: int = Field(gt=0, le=120)
    collateral: Collateral = Collateral.none


class RecommendItem(CamelModel):
    product: Product
    best: bool = Field(description="Лучший вариант под запрос")
    reasons: list[str]
    caveat: str | None = None


class RecommendResponse(CamelModel):
    summary: str
    items: list[RecommendItem]
    