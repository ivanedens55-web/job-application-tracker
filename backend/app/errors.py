"""One consistent JSON error format: {"error": {"code", "message", "details"?}}."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("jobtracker")


class ApiError(Exception):
    """Raise this from routes for any expected error the client should see."""

    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message


def error_response(status_code: int, code: str, message: str, details=None, headers=None):
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body, headers=headers)


def internal_error_response() -> JSONResponse:
    return error_response(500, "internal_error", "Something went wrong on our side. Please try again.")


def _field_name(loc: tuple) -> str:
    # loc looks like ("body", "company") or ("query", "status"); drop the first part.
    parts = [str(p) for p in loc[1:]] or [str(p) for p in loc]
    return ".".join(parts) if parts else "request"


def _clean_message(msg: str) -> str:
    # Our own validators' messages come prefixed with "Value error, ".
    return msg.removeprefix("Value error, ")


async def handle_api_error(request: Request, exc: ApiError):
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return error_response(exc.status_code, exc.code, exc.message, headers=headers)


async def handle_validation_error(request: Request, exc: RequestValidationError):
    # Only the field name and pydantic's short message are returned; never the raw input.
    details = [{"field": _field_name(tuple(e["loc"])), "message": _clean_message(e["msg"])}
               for e in exc.errors()]
    first = details[0] if details else {"field": "request", "message": "Invalid request"}
    message = f"{first['field']}: {first['message']}"
    return error_response(422, "validation_error", message, details)


async def handle_http_error(request: Request, exc: StarletteHTTPException):
    # Framework-raised errors, e.g. unknown URL (404) or wrong method (405).
    if exc.status_code == 404:
        return error_response(404, "not_found", "The requested resource was not found.")
    if exc.status_code == 405:
        return error_response(405, "method_not_allowed", "This method is not allowed on this URL.")
    logger.warning("HTTP %s on %s %s", exc.status_code, request.method, request.url.path)
    return error_response(exc.status_code, "internal_error", "The request could not be completed.")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, handle_api_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_error)
