from pydantic import Field

from app.schemas.base import CamelModel
from app.schemas.enums import Role
from app.schemas.company import Company


class TestAccount(CamelModel):
    id: str = Field(examples=["prodmarket"])
    role: Role
    inn: str | None = Field(default=None, examples=["1655482318"])
    name: str = Field(examples=["ООО \"Продмаркет\""])
    hint: str = Field(examples=["Заявка с контрпредложением - пройдите сделку до выдачи"])


class LoginRequest(CamelModel):
    account_id: str = Field(min_length=1, examples=["prodmarket"])


class User(CamelModel):
    account_id: str
    role: Role
    name: str
    inn: str | None = None


class LoginResponse(CamelModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Время жизни токена, с")
    user: User


class Me(CamelModel):
    user: User
    company: Company | None = Field(default=None, description="Компания клиента; у аналитика - null")
    current_application_id: str | None = Field(
        default = None, description="Последняя незавершенная заявка клиента (при наличии)"
    )
