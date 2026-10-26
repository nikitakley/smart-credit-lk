"""Ошибки симулятора в формате {"error": {"code", "message"}}."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class SourceError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(SourceError)
    async def source_error(_: Request, exc: SourceError) -> JSONResponse:
        return _response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def bad_request(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0]
        place = ".".join(str(p) for p in first["loc"][1:]) or "request"
        return _response(400, "bad_request", f"{place}: {first['msg']}")
