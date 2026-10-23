"""Единый формат ошибок API.

Любая ошибка возвращается в виде словаря:
    {"error": {"code": "...", "message": "...", "fields": [{"field", "code", "message"}]}}

HTTP-коды:
    401 [unauthorized] - нет или недействителен токен
    403 [forbidden] - недостаточно прав
    404 [*_not_found] - объект не найден или недоступен пользователю
    409 [conflict] - действие недопустимо в текущем статусе заявки
    422 [validation_error] - ошибки валидации входных данных (и invalid_code при подписании)
    500 [internal_error] - непредвиденная ошибка сервера
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


# Готовые ошибки, которые часто встречаются
def unauthorized() -> ApiError:
    return ApiError(401, "unauthorized", "Требуется вход в систему")


def forbidden() -> ApiError:
    return ApiError(403, "forbidden", "Недостаточно прав для этого действия")


def not_found(entity: str, message: str) -> ApiError:
    return ApiError(404, f"{entity}_not_found", message)


def conflict(code: str, message: str) -> ApiError:
    return ApiError(409, code, message)


def validation_error(fields: list[FieldError], message: str = "Проверьте введеные данные") -> ApiError:
    return ApiError(422, "validation_error", message, fields)


def _response(status_code: int, body: ErrorBody) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(error=body).model_dump(by_alias=True),
    )


def _field_path(loc: tuple) -> str:
    parts = [str(p) for p in loc if p not in ("body", "query", "path", "header")]
    return ".".join(to_camel(p) if not p.isdigit() else p for p in parts) or "body"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        return _response(exc.status_code, ErrorBody(code=exc.code, message=exc.message, field=exc.fields))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [
            FieldError(field=_field_path(tuple(err.get("loc", ()))), code=err.get("type", "invalid"), message=err.get("msg", ""))
            for err in exc.errors()
        ]
        return _response(422, ErrorBody(code="validation_error", message="Проверьте введенные данные", fields=fields))

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        codes = {404: "not_found", 405: "method_not_allowed", 401: "unauthorized", 403: "forbidden"}
        code = codes.get(exc.status_code, "http_error")
        return _response(exc.status_code, ErrorBody(code=code, message=str(exc.detail)))

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error", exc_info=exc)
        return _response(500, ErrorBody(code="internal_error", message="Внутренняя ошибка сервера"))


def error_responses(*codes: int) -> dict[int | str, dict]:
    "Описание ошибок для OpenAPI."
    descriptions = {
        401: "Нет или недействителен токен",
        403: "Недостаточно прав",
        404: "Объект не найден",
        409: "Действие недопустимо в текущем статусе",
        422: "Ошибка валидации",
    }
    return {code: {"model": ErrorResponse, "description": descriptions.get(code, "Ошибка")} for code in codes}
