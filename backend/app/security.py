"""JWT-авторизация и проверка ролей."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.schemas.enums import Role
from app.schemas.auth import User
from app.errors import forbidden, unauthorized

bearer_scheme = HTTPBearer(auto_error=False, description="JWT из POST /api/auth/login")


def create_access_token(user: User) -> tuple[str, int]:
    settings = get_settings()
    ttl = timedelta(minutes=settings.jwt_ttl_minutes)
    now = datetime.now(UTC)
    payload = {
        "sub": user.account_id,
        "role": user.role.value,
        "name": user.name,
        "inn": user.inn,
        "iat": now,
        "exp": now + ttl,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, int(ttl.total_seconds())


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized()
    settings = get_settings()
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise unauthorized() from exc
    return User(account_id=payload["sub"], role=Role(payload["role"]), name=payload["name"], inn=payload.get("inn"))


def require_client(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != Role.client or not user.inn:
        raise forbidden()
    return user


def require_analyst(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != Role.analyst:
        raise forbidden()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
ClientUser = Annotated[User, Depends(require_client)]
AnalystUser = Annotated[User, Depends(require_analyst)]
