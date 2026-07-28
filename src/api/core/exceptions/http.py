from __future__ import annotations

from http import HTTPStatus
from typing import Any, cast

from pydantic import validate_call
from fastapi import HTTPException

from api.core.schemas import HTTPErrorPM

_REGISTRY_EXCEPTION_CODE: dict[str, type[BaseHTTPException]] = {}
_REGISTRY_EXCEPTION_NAME: dict[str, type[BaseHTTPException]] = {}
_REGISTRY_EXCEPTION_STATUS: dict[int, list[type[BaseHTTPException]]] = {}


class BaseHTTPException(HTTPException):
    error: HTTPErrorPM

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        if cls is BaseHTTPException:
            return

        if not hasattr(cls, "error"):
            raise TypeError(f"{cls.__name__} must define class variable 'error'.")

        _REGISTRY_EXCEPTION_CODE[cls.error.code] = cls
        _REGISTRY_EXCEPTION_NAME[cls.error.name] = cls
        _REGISTRY_EXCEPTION_STATUS.setdefault(cls.error.status_code, []).append(cls)

    @validate_call(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        status_code: int | None = None,
        message: str | None = None,
        data: Any = None,
        description: str | None = None,
        detail: Any = None,
        headers: dict[str, str] | None = None,
        error: HTTPErrorPM | None = None,
    ):
        if error:
            self.error = error.model_copy(deep=True)
        else:
            self.error = self.error.model_copy(deep=True)

        _error_dict = self.error.model_dump(mode="json")

        if not status_code:
            status_code = cast(int, _error_dict.get("status_code", 500))

        if not message:
            message = _error_dict.get("message", "An error occurred")

        if description:
            _error_dict["description"] = description

        if detail:
            _error_dict["detail"] = detail

        super().__init__(
            status_code=status_code,
            detail={"message": message, "data": data, "error": _error_dict},
            headers=headers,
        )


class SuccessError(BaseHTTPException):
    # For security reasons, use generic success message instead of exposing sensitive information.
    error = HTTPErrorPM(
        code="200_00000",
        name="SUCCESS",
        status_code=200,
        message=f"{HTTPStatus(200).phrase}!",
        description=f"{HTTPStatus(200).description}.",
    )


class BadRequestError(BaseHTTPException):
    error = HTTPErrorPM(
        code="400_00000",
        name="BAD_REQUEST",
        status_code=400,
        message=f"{HTTPStatus(400).phrase}!",
        description=f"{HTTPStatus(400).description}.",
    )


class UnauthorizedError(BaseHTTPException):
    error = HTTPErrorPM(
        code="401_00000",
        name="UNAUTHORIZED",
        status_code=401,
        message=f"{HTTPStatus(401).phrase}!",
        description=f"{HTTPStatus(401).description}.",
    )


class TokenMissingError(BaseHTTPException):
    error = HTTPErrorPM(
        code="401_01000",
        name="TOKEN_MISSING",
        status_code=401,
        message="Token is missing!",
        description=f"{HTTPStatus(401).description}.",
    )


class TokenInvalidError(BaseHTTPException):
    error = HTTPErrorPM(
        code="401_01001",
        name="TOKEN_INVALID",
        status_code=401,
        message="Token is invalid!",
        description=f"{HTTPStatus(401).description}.",
    )


class TokenExpiredError(BaseHTTPException):
    error = HTTPErrorPM(
        code="401_01002",
        name="TOKEN_EXPIRED",
        status_code=401,
        message="Token has expired!",
        description=f"{HTTPStatus(401).description}.",
    )


class APIKeyMissingError(BaseHTTPException):
    error = HTTPErrorPM(
        code="401_02000",
        name="API_KEY_MISSING",
        status_code=401,
        message="API key is missing!",
        description=f"{HTTPStatus(401).description}.",
    )


class APIKeyInvalidError(BaseHTTPException):
    error = HTTPErrorPM(
        code="401_02001",
        name="API_KEY_INVALID",
        status_code=401,
        message="API key is invalid!",
        description=f"{HTTPStatus(401).description}.",
    )


class APIKeyExpiredError(BaseHTTPException):
    error = HTTPErrorPM(
        code="401_02002",
        name="API_KEY_EXPIRED",
        status_code=401,
        message="API key has expired!",
        description=f"{HTTPStatus(401).description}.",
    )


class ForbiddenError(BaseHTTPException):
    error = HTTPErrorPM(
        code="403_00000",
        name="FORBIDDEN",
        status_code=403,
        message=f"{HTTPStatus(403).phrase}!",
        description=f"{HTTPStatus(403).description}.",
    )


class NotVerifiedError(BaseHTTPException):
    error = HTTPErrorPM(
        code="403_00001",
        name="NOT_VERIFIED",
        status_code=403,
        message="Not verified!",
        description=f"{HTTPStatus(403).description}.",
    )


class NotFoundError(BaseHTTPException):
    error = HTTPErrorPM(
        code="404_00000",
        name="NOT_FOUND",
        status_code=404,
        message=f"{HTTPStatus(404).phrase}!",
        description=f"{HTTPStatus(404).description}.",
    )


class MethodNotAllowedError(BaseHTTPException):
    error = HTTPErrorPM(
        code="405_00000",
        name="METHOD_NOT_ALLOWED",
        status_code=405,
        message=f"{HTTPStatus(405).phrase}!",
        description=f"{HTTPStatus(405).description}.",
    )


class NotAcceptableError(BaseHTTPException):
    error = HTTPErrorPM(
        code="406_00000",
        name="NOT_ACCEPTABLE",
        status_code=406,
        message=f"{HTTPStatus(406).phrase}!",
        description=f"{HTTPStatus(406).description}.",
    )


class RequestTimeoutError(BaseHTTPException):
    error = HTTPErrorPM(
        code="408_00000",
        name="REQUEST_TIMEOUT",
        status_code=408,
        message=f"{HTTPStatus(408).phrase}!",
        description=f"{HTTPStatus(408).description}.",
    )


class ConflictError(BaseHTTPException):
    error = HTTPErrorPM(
        code="409_00000",
        name="CONFLICT",
        status_code=409,
        message=f"{HTTPStatus(409).phrase}!",
        description=f"{HTTPStatus(409).description}.",
    )


class RequestEntityTooLargeError(BaseHTTPException):
    error = HTTPErrorPM(
        code="413_00000",
        name="REQUEST_ENTITY_TOO_LARGE",
        status_code=413,
        message=f"{HTTPStatus(413).phrase}!",
        description=f"{HTTPStatus(413).description}.",
    )


class RequestURITooLongError(BaseHTTPException):
    error = HTTPErrorPM(
        code="414_00000",
        name="REQUEST_URI_TOO_LONG",
        status_code=414,
        message=f"{HTTPStatus(414).phrase}!",
        description=f"{HTTPStatus(414).description}.",
    )


class UnprocessableEntityError(BaseHTTPException):
    error = HTTPErrorPM(
        code="422_00000",
        name="UNPROCESSABLE_ENTITY",
        status_code=422,
        message=f"{HTTPStatus(422).phrase}!",
        description=f"{HTTPStatus(422).description}.",
    )


class LockedError(BaseHTTPException):
    error = HTTPErrorPM(
        code="423_00000",
        name="LOCKED",
        status_code=423,
        message=f"{HTTPStatus(423).phrase}!",
        description=f"{HTTPStatus(423).description}.",
    )


class TooManyRequestsError(BaseHTTPException):
    error = HTTPErrorPM(
        code="429_00000",
        name="TOO_MANY_REQUESTS",
        status_code=429,
        message=f"{HTTPStatus(429).phrase}!",
        description=f"{HTTPStatus(429).description}.",
    )


class InternalServerError(BaseHTTPException):
    error = HTTPErrorPM(
        code="500_00000",
        name="INTERNAL_SERVER_ERROR",
        status_code=500,
        message=f"{HTTPStatus(500).phrase}!",
        description=f"{HTTPStatus(500).description}.",
    )


class DBError(BaseHTTPException):
    error = HTTPErrorPM(
        code="500_10000",
        name="DB_ERROR",
        status_code=500,
        message=f"{HTTPStatus(500).phrase}!",
        description=f"{HTTPStatus(500).description}.",
    )


class DBPkError(BaseHTTPException):
    error = HTTPErrorPM(
        code="500_10001",
        name="DB_PK_ERROR",
        status_code=500,
        message=f"{HTTPStatus(500).phrase}!",
        description=f"{HTTPStatus(500).description}.",
    )


class DBUqError(BaseHTTPException):
    error = HTTPErrorPM(
        code="500_10002",
        name="DB_UQ_ERROR",
        status_code=500,
        message=f"{HTTPStatus(500).phrase}!",
        description=f"{HTTPStatus(500).description}.",
    )


class SMTPError(BaseHTTPException):
    error = HTTPErrorPM(
        code="500_20000",
        name="SMTP_ERROR",
        status_code=500,
        message=f"{HTTPStatus(500).phrase}!",
        description=f"{HTTPStatus(500).description}.",
    )


class ServiceUnavailableError(BaseHTTPException):
    error = HTTPErrorPM(
        code="503_00000",
        name="SERVICE_UNAVAILABLE",
        status_code=503,
        message=f"{HTTPStatus(503).phrase}!",
        description=f"{HTTPStatus(503).description}.",
    )


class DBConnectError(BaseHTTPException):
    error = HTTPErrorPM(
        code="503_10000",
        name="DB_CONNECT_ERROR",
        status_code=503,
        message=f"{HTTPStatus(503).phrase}!",
        description=f"{HTTPStatus(503).description}.",
    )


class SMTPConnectError(BaseHTTPException):
    error = HTTPErrorPM(
        code="503_20000",
        name="SMTP_CONNECT_ERROR",
        status_code=503,
        message=f"{HTTPStatus(503).phrase}!",
        description=f"{HTTPStatus(503).description}.",
    )


def get_by_code(code: str, **kwargs) -> BaseHTTPException:
    _http_exception_class = _REGISTRY_EXCEPTION_CODE.get(code)
    if not _http_exception_class:
        raise ValueError(f"Not found any HTTP exception class for error code: {code}")

    return _http_exception_class(**kwargs)


def get_by_name(name: str, **kwargs) -> BaseHTTPException:
    _http_exception_class = _REGISTRY_EXCEPTION_NAME.get(name)
    if not _http_exception_class:
        raise ValueError(f"Not found any HTTP exception class for error name: {name}")

    return _http_exception_class(**kwargs)


def get_by_status(status_code: int, **kwargs) -> BaseHTTPException:
    _http_exception_classes = _REGISTRY_EXCEPTION_STATUS.get(status_code, [])
    if not _http_exception_classes:
        raise ValueError(
            f"Not found any HTTP exception class for status code: {status_code}"
        )

    _http_exception_class = _http_exception_classes[0]
    return _http_exception_class(**kwargs)


__all__ = [
    "HTTPErrorPM",
    "BaseHTTPException",
    "SuccessError",
    "BadRequestError",
    "UnauthorizedError",
    "TokenMissingError",
    "TokenInvalidError",
    "TokenExpiredError",
    "APIKeyMissingError",
    "APIKeyInvalidError",
    "APIKeyExpiredError",
    "ForbiddenError",
    "NotVerifiedError",
    "NotFoundError",
    "MethodNotAllowedError",
    "NotAcceptableError",
    "RequestTimeoutError",
    "ConflictError",
    "RequestEntityTooLargeError",
    "RequestURITooLongError",
    "UnprocessableEntityError",
    "LockedError",
    "TooManyRequestsError",
    "InternalServerError",
    "DBError",
    "DBPkError",
    "DBUqError",
    "SMTPError",
    "ServiceUnavailableError",
    "DBConnectError",
    "SMTPConnectError",
    "get_by_code",
    "get_by_name",
    "get_by_status",
]
