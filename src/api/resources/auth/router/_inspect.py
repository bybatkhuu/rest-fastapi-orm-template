from typing import Any

from pydantic import SecretStr
from fastapi import Request, HTTPException, Depends, Security, Form, Cookie
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound

from potato_util.constants import JWT_REGEX
from potato_util.validator import is_valid

from api.core.exceptions import http as http_errors
from api.core.dependencies import db as db_deps
from api.resources.user.schemas import UserOutPM
from api.logger import Logger

from ..schemas import TokenTypeHintEnum, IntrospectOutPM
from .. import dependencies as auth_deps
from .. import service
from ._base import router, RESOURCE_NAME


@router.post(
    "/introspect",
    summary="Introspect Token",
    response_model=IntrospectOutPM,
    response_class=JSONResponse,
    responses={422: {}},
)
async def post_introspect(
    request: Request,
    token: SecretStr | None = Form(
        default=None,
        min_length=16,
        max_length=4096,
        title="Token",
        description="Token to inspect.",
        examples=[
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwia"
            "WF0IjoxNTE2MjM5MDIyfQ.t42p4AHef69Tyyi88U6-p0utZYYrg7mmCGhoAd7Zffs"
        ],
    ),
    refresh_token: SecretStr | None = Cookie(
        default=None,
        min_length=16,
        max_length=4096,
        title="Refresh Token",
        description="Refresh token as cookie to inspect.",
    ),
    token_type_hint: TokenTypeHintEnum = Form(
        default=TokenTypeHintEnum.access_token,
        title="Token Type Hint",
        description="Token type hint to inspect the token.",
        examples=[TokenTypeHintEnum.access_token],
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_read),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Inspecting '{token_type_hint.value}' type token...")

    _token: SecretStr | None = None
    if token:
        _token = token
    elif refresh_token and (token_type_hint == TokenTypeHintEnum.refresh_token):
        _token = refresh_token

    if not _token:
        raise http_errors.UnprocessableEntityError(message="Token is missing!")

    if not is_valid(val=_token.get_secret_value(), pattern=JWT_REGEX):
        raise http_errors.UnprocessableEntityError(message="Invalid token!")

    _output_dict: dict[str, Any] = {"active": False}
    try:
        _output_dict = await service.async_introspect(
            async_session=db_session,
            token=_token,
            token_type_hint=token_type_hint,
            logger=_logger,
        )

        _logger.success(f"Successfully inspected '{token_type_hint.value}' type token.")
    except HTTPException:
        raise
    except Exception:
        _logger.exception(f"Failed to inspect '{token_type_hint.value}' type token!")
        raise http_errors.InternalServerError(message="Failed to inspect token!")

    return _output_dict


@router.get(
    "/userinfo",
    summary="Get User Info",
    response_model=UserOutPM,
    response_class=JSONResponse,
    responses={401: {}, 403: {}, 422: {}},
)
async def get_userinfo(
    request: Request,
    auth_user_id: str = Security(
        auth_deps.auth_any, scopes=[f"{RESOURCE_NAME}:userinfo"]
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_read),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Getting user info ('{auth_user_id}' ID)...")

    _user_dict: dict[str, Any]
    try:
        _user_dict = await service.async_userinfo(
            async_session=db_session, user_id=auth_user_id, logger=_logger
        )

        _logger.success(f"Successfully got the user info ('{auth_user_id}' ID).")
    except HTTPException:
        raise
    except NoResultFound:
        _logger.warning(
            f"[ANOMALY] - Attempting to get user info ('{auth_user_id}' ID) but user is not found from the database!"
        )
        raise http_errors.UnprocessableEntityError(
            message="Invalid access token!",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )
    except Exception:
        _logger.exception(f"Failed to get the user info ('{auth_user_id}' ID)!")
        raise http_errors.InternalServerError(message="Failed to get the user info!")

    return _user_dict


__all__ = [
    "post_introspect",
    "get_userinfo",
]
