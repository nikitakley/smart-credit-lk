"""Единый формат ошибок API.

Любая ошибка возвращается в виде словаря:
    {"error": {"code": "...", "message": "...", "fields": [{"field", "code", "message"}]}}

HTTP-коды:
    401 [unauthorized]       — нет или недействителен токен
    403 [forbidden]          — не хватает прав (роль)
    404 [*_not_found]        — объект не найден или недоступен пользователю
    409 [конфликт состояния] — действие недопустимо в текущем статусе заявки (коды — CONFLICT_CODES)
    422 [validation_error]   — ошибки валидации входных данных (и invalid_code при подписании)
    500 [internal_error]     — непредвиденная ошибка сервера
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic.alias_generators import to_camel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.base import CamelModel

logger = logging.getLogger(__name__)


class FieldError(CamelModel):
    field: str
    code: str
    message: str


class ErrorBody(CamelModel):
    code: str
    message: str
    fields: list[FieldError] = []


class ErrorResponse(CamelModel):
    error: ErrorBody


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        fields: list[FieldError] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.fields = fields or []


# Готовые ошибки, которые встречаются часто
def unauthorized() -> ApiError:
    return ApiError(401, "unauthorized", "Требуется вход в систему")


def forbidden() -> ApiError:
    return ApiError(403, "forbidden", "Недостаточно прав для этого действия")


def not_found(entity: str, message: str) -> ApiError:
    return ApiError(404, f"{entity}_not_found", message)


def conflict(code: str, message: str) -> ApiError:
    return ApiError(409, code, message)


def validation_error(fields: list[FieldError], message: str = "Проверьте введённые данные") -> ApiError:
    return ApiError(422, "validation_error", message, fields)


def _response(status_code: int, body: ErrorBody) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(error=body).model_dump(by_alias=True),
    )


def _field_path(loc: tuple) -> str:
    # ("body", "contact", "phone") -> "contact.phone"; служебные части пути отбрасываем
    parts = [str(p) for p in loc if p not in ("body", "query", "path", "header")]
    return ".".join(to_camel(p) if not p.isdigit() else p for p in parts) or "body"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        return _response(exc.status_code, ErrorBody(code=exc.code, message=exc.message, fields=exc.fields))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [
            FieldError(field=_field_path(tuple(err.get("loc", ()))), code=err.get("type", "invalid"), message=err.get("msg", ""))
            for err in exc.errors()
        ]
        return _response(422, ErrorBody(code="validation_error", message="Проверьте введённые данные", fields=fields))

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        codes = {404: "not_found", 405: "method_not_allowed", 401: "unauthorized", 403: "forbidden"}
        code = codes.get(exc.status_code, "http_error")
        return _response(exc.status_code, ErrorBody(code=code, message=str(exc.detail)))

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error", exc_info=exc)
        return _response(500, ErrorBody(code="internal_error", message="Внутренняя ошибка сервера"))


# Все коды ошибок 409. Любой код, который выдаёт сервис, должен быть здесь: из этого словаря
# строится описание в OpenAPI, а тест test_conflict_codes_are_documented проверяет полноту.
CONFLICT_CODES = {
    "not_draft": "заявка уже не черновик",
    "invalid_transition": "действие недопустимо в текущем статусе заявки",
    "concurrent_update": "заявку одновременно изменил другой запрос — перечитайте её и повторите действие",
    "no_offer": "нет действующего предложения банка",
    "offer_expired": "срок действия предложения истёк",
    "not_signing": "договор сейчас не на подписании",
    "code_not_requested": "код подписи ещё не запрашивался",
    "code_expired": "срок действия кода подписи истёк",
    "code_attempts_exceeded": "попытки ввода кода закончились — нужен новый код",
    "no_info_request": "банк не запрашивал дополнительную информацию",
    "decision_not_allowed": "решение по заявке в этом статусе не принимается",
    "checks_refresh_not_allowed": "в этом статусе данные из источников не запрашиваются",
    "not_submitted": "заявка ещё не подана",
}


def error_responses(*codes: int, conflicts: tuple[str, ...] = ()) -> dict[int | str, dict]:
    """Описание ошибок для OpenAPI: error_responses(401, 404, 409, conflicts=("not_draft", "concurrent_update"))."""
    descriptions = {
        401: "Нет или недействителен токен (`unauthorized`)",
        403: "Недостаточно прав (`forbidden`)",
        404: "Объект не найден или недоступен пользователю (`*_not_found`)",
        409: "Действие недопустимо в текущем состоянии заявки",
        422: "Ошибка валидации (`validation_error`, подробности в `fields`)",
    }
    if conflicts:
        # KeyError при запуске, если код не описан в CONFLICT_CODES, — опечатку заметим сразу
        descriptions[409] += ". Коды:\n" + "\n".join(f"- `{c}` — {CONFLICT_CODES[c]}" for c in conflicts)
    return {code: {"model": ErrorResponse, "description": descriptions.get(code, "Ошибка")} for code in codes}
