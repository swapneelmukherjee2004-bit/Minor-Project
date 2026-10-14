import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger(__name__)


def _body(code: str, message: str, details=None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def install(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api(_: Request, e: ApiError):
        return JSONResponse(_body(e.code, e.message), status_code=e.status)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, e: StarletteHTTPException):
        return JSONResponse(_body("http_error", str(e.detail)), status_code=e.status_code)

    @app.exception_handler(RequestValidationError)
    async def _val(_: Request, e: RequestValidationError):
        details = [{"field": ".".join(str(x) for x in err["loc"][1:]), "message": err["msg"]} for err in e.errors()]
        return JSONResponse(_body("validation_error", "Request validation failed.", details), status_code=422)

    @app.exception_handler(RateLimitExceeded)
    async def _rate(_: Request, e: RateLimitExceeded):
        return JSONResponse(_body("rate_limited", "Too many requests. Please slow down and retry shortly."), status_code=429)

    @app.exception_handler(SQLAlchemyError)
    async def _db(_: Request, e: SQLAlchemyError):
        log.exception("database error")
        return JSONResponse(_body("database_error", "A database error occurred."), status_code=500)

    @app.exception_handler(Exception)
    async def _any(_: Request, e: Exception):
        log.exception("unhandled error")
        return JSONResponse(_body("internal_error", "An unexpected error occurred."), status_code=500)
