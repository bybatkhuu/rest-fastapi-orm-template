from ipaddress import ip_address

from pydantic import EmailStr
from fastapi import Request, HTTPException, Depends, Form
from sqlalchemy.ext.asyncio import AsyncSession

from potato_util.http.fastapi import get_base_url

from api.core.exceptions import http as http_errors
from api.core.dependencies import db as db_deps
from api.core.schemas import BaseResPM
from api.core.responses import BaseResponse
from api.logger import Logger

from ..schemas import UserResetPasswordPM
from .. import service
from ._base import router


@router.post(
    "/forgot-password",
    summary="Forgot Password",
    status_code=202,
    response_model=BaseResPM,
    responses={400: {}, 403: {}, 422: {}},
)
async def post_forgot_password(
    request: Request,
    email: EmailStr = Form(
        ...,
        title="Email",
        description="Email address to send the reset password mail.",
        examples=["user@example.com"],
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Forgot password for user with '{email}' email...")

    _response = BaseResponse(
        request=request,
        status_code=202,
        message="Sent reset password mail, if email is registered and active.",
    )

    try:
        _base_url = get_base_url(request)
        await service.async_forgot_password(
            async_session=db_session, email=email, base_url=_base_url, logger=_logger
        )
        await db_session.commit()

        _logger.success(f"Successfully sent reset password mail to '{email}' email.")
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            if (200 <= err.status_code) and (err.status_code < 300):
                return _response
            raise

        _logger.exception(f"Failed to send reset password mail to '{email}' email!")
        raise http_errors.InternalServerError(
            message="Failed to send reset password mail!"
        )

    return _response


@router.post(
    "/reset-password",
    summary="Reset Password",
    response_model=BaseResPM,
    responses={
        401: {
            "description": """Reset token has expired or invalid!

Error codes|Description
---|---
`401_01000`|Reset token is missing!
`401_01001`|Reset token is invalid!
`401_01002`|Reset token has expired!
""",
        },
        403: {},
        422: {},
    },
)
async def post_reset_password(
    request: Request,
    user_reset_password: UserResetPasswordPM = Form(
        ...,
        title="User Reset Password Data",
        description="Form data to reset the user password with reset token.",
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info("Resetting the user password with token...")

    try:
        _client_host = ip_address("0.0.0.0")
        if request.client:
            _client_host = ip_address(request.client.host)

        if hasattr(request.state, "client_host"):
            _client_host = ip_address(request.state.client_host)

        await service.async_reset_password(
            async_session=db_session,
            user_reset_password=user_reset_password,
            client_host=_client_host,
            logger=_logger,
        )
        await db_session.commit()

        _logger.success("Successfully reset the user password with token.")
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception("Failed to reset the user password with token!")
        raise http_errors.InternalServerError(
            message="Failed to reset the user password!"
        )

    _response = BaseResponse(
        request=request, message="Successfully reset the user password."
    )
    if user_reset_password.logout_all:
        _response.delete_cookie(key="access_token")
        _response.delete_cookie(key="refresh_token")

    return _response


__all__ = [
    "post_forgot_password",
    "post_reset_password",
]
