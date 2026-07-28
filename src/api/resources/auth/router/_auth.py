from ipaddress import ip_address
from datetime import timezone, datetime

from pydantic import SecretStr
from fastapi import Request, Response, HTTPException, Depends, Form, Body, Cookie
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from potato_util.constants import JWT_REGEX, EnvEnum
from potato_util.validator import is_valid

from api.core.exceptions import http as http_errors
from api.core.schemas import BaseResPM
from api.core.responses import BaseResponse
from api.core.dependencies import db as db_deps
from api.config import config
from api.logger import Logger

from ..schemas import (
    UserLoginPM,
    AuthTokensOutPM,
    TokenGrantTypeEnum,
    TokenRevokeTypeEnum,
)
from .. import service
from ._base import router


@router.post(
    "/login",
    summary="Login User",
    response_model=AuthTokensOutPM,
    response_class=JSONResponse,
    responses={401: {}, 403: {}, 422: {}},
)
async def post_login(
    request: Request,
    user_login: UserLoginPM = Form(
        ..., title="User Login Data", description="Form data to login the user."
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Logging in user with '{user_login.email}' email and password...")

    _is_browser: bool = request.state.is_browser
    _auth_tokens_pm: AuthTokensOutPM
    _refresh_expires_at: datetime
    _refresh_token: SecretStr
    try:
        _client_host = ip_address("0.0.0.0")
        if request.client:
            _client_host = ip_address(request.client.host)

        if hasattr(request.state, "client_host"):
            _client_host = ip_address(request.state.client_host)

        _auth_tokens_pm, _refresh_expires_at = await service.async_login(
            async_session=db_session,
            user_login=user_login,
            client_host=_client_host,
            logger=_logger,
        )
        assert _auth_tokens_pm.refresh_token, "Refresh token always set by async_login!"
        _refresh_token = SecretStr(_auth_tokens_pm.refresh_token)
        if config.api.security.cookie.enabled and _is_browser:
            _auth_tokens_pm.refresh_token = None

        await db_session.commit()

        _logger.success(f"Successfully logged in user with '{user_login.email}' email.")
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception(
            f"Failed to login user with '{user_login.email}' email and password!"
        )
        raise http_errors.InternalServerError(
            message="Failed to login user with email and password!"
        )

    _response = JSONResponse(content=_auth_tokens_pm.model_dump(mode="json"))

    if config.api.security.cookie.enabled and _is_browser:
        _cookie_secure = False
        if (
            (config.env == EnvEnum.PRODUCTION)
            or (config.env == EnvEnum.STAGING)
            or config.api.security.ssl.enabled
        ):
            _cookie_secure = True

        _refresh_expires_at = _refresh_expires_at.astimezone(timezone.utc)
        _response.set_cookie(
            key="access_token",
            value=_auth_tokens_pm.access_token,
            expires=_refresh_expires_at,
            secure=_cookie_secure,
            samesite="strict",
        )

        _response.set_cookie(
            key="refresh_token",
            value=_refresh_token.get_secret_value(),
            expires=_refresh_expires_at,
            path=f"{config.api.prefix}/auth",
            httponly=True,
            secure=_cookie_secure,
            samesite="strict",
        )

    return _response


@router.post(
    "/token",
    summary="Issue Tokens",
    description="""Currently only supports the **`refresh_token`** grant type.

Grant type|Description
---|---
**`refresh_token`**|Refresh token to issue new tokens.

## A. Refresh Token Grant Type

At least one of the following fields must be provided:
- **`refresh_token`** in **form data** (Higher priority)
- **`refresh_token`** in **cookie** (Only for browser requests)

If both are provided, the **form data** field will be used and the **cookie** field will be ignored.
If none is provided, an error will be returned!
""",
    response_model=AuthTokensOutPM,
    response_class=JSONResponse,
    responses={
        401: {"description": """Token has expired or invalid!

Error codes|Description
---|---
`401_01000`|Token is missing!
`401_01001`|Token is invalid!
`401_01002`|Token has expired!
"""},
        403: {},
        422: {},
    },
)
async def post_token(
    request: Request,
    grant_type: TokenGrantTypeEnum = Form(
        default=TokenGrantTypeEnum.refresh_token,
        title="Grant Type",
        description="Grant type to issue user tokens.",
        examples=["refresh_token"],
    ),
    refresh_token_form: SecretStr | None = Form(
        default=None,
        min_length=16,
        max_length=4096,
        alias="refresh_token",
        title="Refresh Token Form",
        description="Form data refresh token to issue tokens.",
        examples=[
            (
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwia"
                "WF0IjoxNTE2MjM5MDIyfQ.t42p4AHef69Tyyi88U6-p0utZYYrg7mmCGhoAd7Zffs"
            )
        ],
    ),
    refresh_token_cookie: SecretStr | None = Cookie(
        default=None,
        min_length=16,
        max_length=4096,
        alias="refresh_token",
        title="Refresh Token Cookie",
        description="Cookie refresh token to issue tokens.",
        examples=[
            (
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwia"
                "WF0IjoxNTE2MjM5MDIyfQ.t42p4AHef69Tyyi88U6-p0utZYYrg7mmCGhoAd7Zffs"
            )
        ],
    ),
    # scope: str | None = Form(
    #     default=None,
    #     max_length=512,
    #     title="Scope",
    #     description="Scope of the access token.",
    # ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info("Issuing user tokens...")

    _is_browser: bool = request.state.is_browser
    _auth_tokens_pm: AuthTokensOutPM
    _refresh_expires_at: datetime
    _new_refresh_token: SecretStr
    try:
        if grant_type == TokenGrantTypeEnum.refresh_token:
            _refresh_token: SecretStr | None = None
            if refresh_token_form:
                _refresh_token = refresh_token_form
            elif refresh_token_cookie:
                _refresh_token = refresh_token_cookie
            else:
                raise http_errors.UnprocessableEntityError(
                    message="Not found any refresh token!"
                )

            if not is_valid(val=_refresh_token.get_secret_value(), pattern=JWT_REGEX):
                _logger.warning(
                    "[ANOMALY] - Attempting to issue tokens with invalid refresh token!"
                )
                raise http_errors.UnprocessableEntityError(
                    message="Invalid refresh token!"
                )

            _client_host = ip_address("0.0.0.0")
            if request.client:
                _client_host = ip_address(request.client.host)

            if hasattr(request.state, "client_host"):
                _client_host = ip_address(request.state.client_host)

            _auth_tokens_pm, _refresh_expires_at = await service.async_refresh(
                async_session=db_session,
                refresh_token=_refresh_token,
                client_host=_client_host,
                logger=_logger,
            )
            assert (
                _auth_tokens_pm.refresh_token
            ), "Refresh token always set by async_login!"
            _new_refresh_token = SecretStr(_auth_tokens_pm.refresh_token)
            if config.api.security.cookie.enabled and _is_browser:
                _auth_tokens_pm.refresh_token = None
        else:
            # TODO: Implement other grant types...
            _logger.warning(f"Not implemented grant type: '{grant_type}'!")
            raise http_errors.UnprocessableEntityError(message="Invalid grant type!")

        await db_session.commit()

        _logger.success("Successfully issued user tokens.")
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception("Failed to issue user tokens!")
        raise http_errors.InternalServerError(message="Failed to issue user tokens!")

    _response = JSONResponse(content=_auth_tokens_pm.model_dump(mode="json"))

    if config.api.security.cookie.enabled and _is_browser:
        _cookie_secure = False
        if (
            (config.env == EnvEnum.PRODUCTION)
            or (config.env == EnvEnum.STAGING)
            or config.api.security.ssl.enabled
        ):
            _cookie_secure = True

        _refresh_expires_at = _refresh_expires_at.astimezone(timezone.utc)
        _response.set_cookie(
            key="access_token",
            value=_auth_tokens_pm.access_token,
            expires=_refresh_expires_at,
            secure=_cookie_secure,
            samesite="strict",
        )
        _response.set_cookie(
            key="refresh_token",
            value=_new_refresh_token.get_secret_value(),
            expires=_refresh_expires_at,
            path=f"{config.api.prefix}/auth",
            httponly=True,
            secure=_cookie_secure,
            samesite="strict",
        )

    return _response


@router.post(
    "/revoke", summary="Revoke Tokens", response_model=BaseResPM, responses={422: {}}
)
async def post_revoke(
    request: Request,
    token: SecretStr = Form(
        ...,
        min_length=16,
        max_length=4096,
        title="Token",
        description="Token to revoke.",
        examples=[
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwia"
            "WF0IjoxNTE2MjM5MDIyfQ.t42p4AHef69Tyyi88U6-p0utZYYrg7mmCGhoAd7Zffs"
        ],
    ),
    token_type_hint: TokenRevokeTypeEnum = Form(
        default=TokenRevokeTypeEnum.refresh_token,
        title="Token Type Hint",
        description="Token type hint to revoke the token.",
        examples=[TokenRevokeTypeEnum.refresh_token],
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    if not is_valid(val=token.get_secret_value(), pattern=JWT_REGEX):
        raise http_errors.UnprocessableEntityError(message="Invalid token!")

    _logger: Logger = request.state.logger
    _logger.info(f"Revoking '{token_type_hint.value}' type token...")

    try:
        await service.async_revoke(
            async_session=db_session,
            token=token,
            token_type_hint=token_type_hint,
            logger=_logger,
        )
        await db_session.commit()

        _logger.success(f"Successfully revoked '{token_type_hint.value}' type token.")
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception(f"Failed to revoke '{token_type_hint.value}' type token!")
        raise http_errors.InternalServerError(message="Failed to revoke token!")

    _response = BaseResponse(request=request, message="Successfully revoked token.")
    return _response


@router.post(
    "/logout",
    summary="Logout User",
    status_code=204,
    response_class=Response,
    responses={422: {}},
)
async def post_logout(
    request: Request,
    response: Response,
    refresh_token_body: SecretStr | None = Body(
        default=None,
        min_length=16,
        max_length=4096,
        alias="refresh_token",
        title="Refresh Token Body",
        description="Body refresh token to logout user.",
        embed=True,
        examples=[
            (
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwia"
                "WF0IjoxNTE2MjM5MDIyfQ.t42p4AHef69Tyyi88U6-p0utZYYrg7mmCGhoAd7Zffs"
            )
        ],
    ),
    access_token: SecretStr | None = Cookie(
        default=None,
        min_length=16,
        max_length=4096,
        title="Access Token",
        description="Access token to logout user.",
        examples=[
            (
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwia"
                "WF0IjoxNTE2MjM5MDIyfQ.t42p4AHef69Tyyi88U6-p0utZYYrg7mmCGhoAd7Zffs"
            )
        ],
    ),
    refresh_token_cookie: SecretStr | None = Cookie(
        default=None,
        min_length=16,
        max_length=4096,
        alias="refresh_token",
        title="Refresh Token Cookie",
        description="Cookie refresh token to logout user.",
        examples=[
            (
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwia"
                "WF0IjoxNTE2MjM5MDIyfQ.t42p4AHef69Tyyi88U6-p0utZYYrg7mmCGhoAd7Zffs"
            )
        ],
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info("Logging out user...")

    _refresh_token: SecretStr | None = None
    if refresh_token_body:
        _refresh_token = refresh_token_body
    elif refresh_token_cookie:
        _refresh_token = refresh_token_cookie

    response.status_code = 204
    if access_token:
        response.delete_cookie(key="access_token")

    if refresh_token_cookie:
        response.delete_cookie(key="refresh_token", path=f"{config.api.prefix}/auth")

    if not _refresh_token:
        _logger.warning("Not found any refresh token to logout user!")
        return response

    if not is_valid(val=_refresh_token.get_secret_value(), pattern=JWT_REGEX):
        raise http_errors.UnprocessableEntityError(message="Invalid refresh token!")

    try:
        await service.async_revoke(
            async_session=db_session,
            token=_refresh_token,
            token_type_hint=TokenRevokeTypeEnum.refresh_token,
            logger=_logger,
        )
        await db_session.commit()

        _logger.success("Successfully logged out user.")
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            return response

        _logger.exception("Failed to logout user!")
        raise http_errors.InternalServerError(message="Failed to logout user!")

    return response


__all__ = [
    "post_login",
    "post_token",
    "post_revoke",
    "post_logout",
]
