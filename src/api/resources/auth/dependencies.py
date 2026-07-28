from typing import cast
from ipaddress import ip_address, ip_network

from pydantic import SecretStr
from jwt import ExpiredSignatureError, InvalidTokenError
from fastapi import Request, Depends, Security
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    APIKeyHeader,
    SecurityScopes,
)
from sqlalchemy.ext.asyncio import AsyncSession

from potato_util.constants import JWT_REGEX, ALPHANUM_HOST_REGEX, WarnEnum
from potato_util import validator
from potato_util.dt import now_utc_dt

from api.core.exceptions import http as http_errors
from api.core.dependencies import db as db_deps
from api.resources.user.schemas import UserStatusEnum
from api.resources.user.model import UserORM
from api.resources.user_api_key.schemas import ApiKeyStatusEnum
from api.resources.user_api_key import service as api_key_service
from api.logger import Logger

from . import utils as auth_utils
from .schemas import AccessTokenPayloadPM

_http_bearer = HTTPBearer(
    auto_error=False,
    scheme_name="Bearer",
    description="Bearer token for authentication.",
)
_api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    scheme_name="API Key",
    description="API key for authentication.",
)


def auth_jwt(
    request: Request,
    security_scopes: SecurityScopes,
    authorization: HTTPAuthorizationCredentials | None = Security(_http_bearer),
) -> AccessTokenPayloadPM:
    """Security dependency function to authenticate the access token (JWT) and get the payload.

    Args:
        request         (Request                     , required): The FastAPI request object.
        security_scopes (SecurityScopes              , required): The security scopes.
        authorization   (HTTPAuthorizationCredentials, required): 'Authorization: Bearer <access_token>'
                                                                    header credentials.

    Raises:
        TokenMissingError: If the access token is missing.
        TokenInvalidError: If the access token is invalid.
        TokenExpiredError: If the access token has expired.
        TokenInvalidError: If the JWT token is not valid.
        ForbiddenError   : If the JWT token does not have enough scope permissions.
        UnauthorizedError: If the access token is from a different IP address than allowed IP address.
        TokenInvalidError: If the access token type is not valid.

    Returns:
        AccessTokenPayloadPM: The decoded access token payload.
    """

    if not authorization:
        raise http_errors.TokenMissingError(
            message="Not authenticated!",
            headers={"WWW-Authenticate": 'Bearer error="missing_token"'},
        )

    _access_token = SecretStr(authorization.credentials)
    _access_token_length = len(_access_token.get_secret_value())
    if (
        (_access_token_length < 16)
        or (4096 < _access_token_length)
        or (
            not validator.is_valid(
                val=_access_token.get_secret_value(), pattern=JWT_REGEX
            )
        )
    ):
        raise http_errors.TokenInvalidError(
            message="Invalid access token!",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )

    _payload: AccessTokenPayloadPM
    try:
        _payload = cast(
            AccessTokenPayloadPM, auth_utils.verify_jwt(token=_access_token)
        )
    except ExpiredSignatureError:
        raise http_errors.TokenExpiredError(
            message="Access token has expired!",
            headers={"WWW-Authenticate": 'Bearer error="expired_token"'},
        )
    except InvalidTokenError:
        raise http_errors.TokenInvalidError(
            message="Invalid access token!",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )

    _required_scopes = set[str](security_scopes.scopes)
    _token_scopes = _payload.scopes

    if _required_scopes:
        _required_scopes.add("all")
        if not _required_scopes.intersection(_token_scopes):
            raise http_errors.ForbiddenError(
                message="Not enough scope permissions!",
                headers={"WWW-Authenticate": 'Bearer error="insufficient_scope"'},
            )

    _id: str | None = None
    if isinstance(_payload, AccessTokenPayloadPM):
        _id = _payload.sub
    else:
        raise http_errors.TokenInvalidError(
            message="Invalid access token!",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )

    _logger: Logger = request.state.logger
    _logger = _logger.bind(user_id=_id)
    request.state.logger = _logger
    return _payload


def get_jwt_sub(
    payload: AccessTokenPayloadPM = Security(auth_jwt),
) -> str:
    """Security dependency function to get the subject ID from the token payload.

    Args:
        payload (AccessTokenPayloadPM, required): The decoded access token payload.

    Returns:
        str: The subject ID.
    """

    _id: str = payload.sub
    return _id


def is_auth(sub_id: str = Security(get_jwt_sub)) -> bool:
    """Security dependency function to check if the subject is authenticated.

    Args:
        sub_id (str, required): The subject ID.

    Returns:
        bool: True if the subject is authenticated, False otherwise.
    """

    if not sub_id:
        return False

    return True


async def auth_api_key(
    request: Request,
    security_scopes: SecurityScopes,
    api_key: str | None = Security(_api_key_header),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
) -> str:
    """Security dependency function to authenticate the API key and get the user ID.

    Args:
        request         (Request       , required): The FastAPI request object.
        security_scopes (SecurityScopes, required): The security scopes.
        api_key         (str | None    , required): 'X-API-Key: <api_key>' header value.
        db_session      (AsyncSession  , required): The database session.

    Raises:
        APIKeyMissingError: If the API key is missing.
        APIKeyInvalidError: If the API key is invalid.
        APIKeyInvalidError: If the API key is not found in the database.
        UnauthorizedError : If the user account is not active.
        APIKeyExpiredError: If the API key has expired.
        APIKeyInvalidError: If the API key is not active.
        ForbiddenError    : If the API key is not allowed from this IP.
        ForbiddenError    : If the API key does not have enough scope permissions.

    Returns:
        str: The user ID.
    """

    if not api_key:
        raise http_errors.APIKeyMissingError(
            message="Not authenticated!",
            headers={"WWW-Authenticate": 'X-API-Key error="missing_api_key"'},
        )

    _api_key_length = len(api_key)
    if (
        (_api_key_length < 32)
        or (128 < _api_key_length)
        or (not validator.is_valid(val=api_key, pattern=ALPHANUM_HOST_REGEX))
    ):
        raise http_errors.APIKeyInvalidError(
            message="Invalid API key!",
            headers={"WWW-Authenticate": 'X-API-Key error="invalid_api_key"'},
        )

    _logger: Logger = request.state.logger
    _api_key_orm = await api_key_service.async_get_by_api_key(
        async_session=db_session,
        api_key=api_key,  # type: ignore
        joins=["user"],
        logger=_logger,
        warn_mode=WarnEnum.DEBUG,
    )

    if not _api_key_orm:
        raise http_errors.APIKeyInvalidError(
            message="Invalid API key!",
            headers={"WWW-Authenticate": 'X-API-Key error="invalid_api_key"'},
        )

    _user_orm: UserORM = _api_key_orm.user
    if _user_orm.status != UserStatusEnum.ACTIVE:
        raise http_errors.UnauthorizedError(
            message="User account is not active!",
            headers={"WWW-Authenticate": 'X-API-Key error="user_not_active"'},
        )

    _current_dt = now_utc_dt()
    if (_api_key_orm.status == ApiKeyStatusEnum.EXPIRED) or (
        _api_key_orm.expires_at and (_api_key_orm.expires_at <= _current_dt)
    ):
        raise http_errors.APIKeyExpiredError(
            message="API key has expired!",
            headers={"WWW-Authenticate": 'X-API-Key error="expired_api_key"'},
        )

    if _api_key_orm.status != ApiKeyStatusEnum.ACTIVE:
        raise http_errors.APIKeyInvalidError(
            message="Invalid API key!",
            headers={"WWW-Authenticate": 'X-API-Key error="invalid_api_key"'},
        )

    _client_host = ip_address("0.0.0.0")
    if request.client:
        _client_host = ip_address(request.client.host)

    if hasattr(request.state, "client_host"):
        _client_host = ip_address(request.state.client_host)

    if _api_key_orm.allowed_ips:
        _is_allowed = False
        for _allowed_ip in _api_key_orm.allowed_ips:
            _allowed_network = ip_network(str(_allowed_ip), strict=False)
            if _client_host in _allowed_network:
                _is_allowed = True
                break

        if not _is_allowed:
            raise http_errors.ForbiddenError(
                message="Not allowed from this IP!",
                headers={"WWW-Authenticate": 'X-API-Key error="not_allowed_ip"'},
            )

    _, _user_scopes = await _user_orm.async_get_permissions()
    _resolved_scopes = _user_scopes
    if _api_key_orm.allowed_scopes:
        _resolved_scopes = _user_scopes.intersection(
            set[str](_api_key_orm.allowed_scopes)
        )

    _required_scopes = set[str](security_scopes.scopes)
    if _required_scopes:
        _required_scopes.add("all")
        if not _required_scopes.intersection(_resolved_scopes):
            raise http_errors.ForbiddenError(
                message="Not enough scope permissions!",
                headers={"WWW-Authenticate": 'X-API-Key error="insufficient_scope"'},
            )

    _api_key_orm.last_used_ip = _client_host
    _api_key_orm.last_used_at = _current_dt
    await db_session.commit()

    _user_id = _user_orm.id
    _logger = _logger.bind(user_id=_user_id)
    request.state.logger = _logger
    return _user_id


async def auth_any(
    request: Request,
    security_scopes: SecurityScopes,
    authorization: HTTPAuthorizationCredentials | None = Security(_http_bearer),
    api_key: str | None = Security(_api_key_header),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
) -> str:
    """Security dependency function to authenticate the subject (user or machine) using either JWT or API key.
    This function will try to authenticate the subject using JWT, if 'Authorization: Bearer <access_token>' exists.
    If 'X-API-Key: <api_key>' exists, it will try to authenticate the subject using API key.
    If both JWT and API key authentication fail, the function will raise a UnauthorizedError
    with error code UNAUTHORIZED.

    Args:
        request         (Request                            , required): The FastAPI request object.
        security_scopes (SecurityScopes                     , required): The security scopes.
        authorization   (HTTPAuthorizationCredentials | None, required): 'Authorization: Bearer <access_token>'
                                                                            header credentials.
        api_key         (str | None                         , required): 'X-API-Key: <api_key>' header value.
        db_session      (AsyncSession                       , required): The database session.

    Raises:
        UnauthorizedError: If the subject is not authenticated.

    Returns:
        str: The subject ID.
    """

    _sub_id: str | None = None
    if authorization:
        _payload = auth_jwt(
            request=request,
            security_scopes=security_scopes,
            authorization=authorization,
        )
        _sub_id = _payload.sub
    elif api_key:
        _sub_id = await auth_api_key(
            request=request,
            security_scopes=security_scopes,
            api_key=api_key,
            db_session=db_session,
        )

    if not _sub_id:
        raise http_errors.UnauthorizedError(
            message="Not authenticated!",
            headers={"WWW-Authenticate": 'error="unauthorized"'},
        )

    return _sub_id


__all__ = [
    "auth_jwt",
    "get_jwt_sub",
    "is_auth",
    "auth_api_key",
    "auth_any",
]
