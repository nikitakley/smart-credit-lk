from datetime import date, datetime

from pydantic import Field

from app.schemas.base import CamelModel
from app.schemas.enums import CompanyStatus, CompanyType


class Okved(CamelModel):
    code: str = Field(examples=["47.11"])
    title: str = Field(examples=["Торговля розничная преимущественно пищевыми продуктами"])


class Founder(CamelModel):
    name: str = Field(examples=["Иванов Иван Иванович"])
    share_percent: float = Field(examples=[100.0])


class Company(CamelModel):
    """Сведения о компании клиента. Предполагается, что клиент уже обслуживается в банке, данные известны заранее"""

    inn: str = Field(examples=["1655482318"])
    type: CompanyType
    status: CompanyStatus
    name: str = Field(examples=["ООО 'Продмаркет'"])
    full_name: str = Field(examples=["Общество с ограниченной ответственностью 'Продмаркет'"])
    ogrn: str = Field(description="ОГРН для юрлица, ОГРНИП для ИП")
    kpp: str | None = Field(default=None, description="У ИП отсутствует")
    registered_at: date
    director: str = Field(description="Руководитель; у ИП - сам предприниматель")
    director_title: str = Field(examples=["Генеральный директор"])
    founders: list[Founder] = Field(default_factory=list, description="Учредители; у ИП - пусто")
    okved: Okved
    legal_address: str
    phone: str
    email: str
    account: str = Field(description="Расчетный счет в банке")
    source: str = Field(default="ФНС", description="Источник реквизитов")
    fetched_at: datetime


class CompanyShort(CamelModel):
    inn: str
    name: str
    type: CompanyType
