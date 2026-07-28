from pydantic import EmailStr, SecretStr
from fastapi import Request, HTTPException, Depends, Form, Body
from sqlalchemy.ext.asyncio import AsyncSession

from potato_util.constants import JWT_REGEX
from potato_util.validator import is_valid
from potato_util.http.fastapi import get_base_url

from api.core.exceptions import http as http_errors
from api.core.dependencies import db as db_deps
from api.core.schemas import BaseResPM
from api.core.responses import BaseResponse
from api.logger import Logger

from ..schemas import UserSignupPM
from .. import service
from ._base import router


@router.post(
    "/signup",
    summary="Signup User",
    status_code=201,
    response_model=BaseResPM,
    responses={
        400: {},
        409: {"description": "Email already registered!"},
        422: {},
    },
)
async def post_signup(
    request: Request,
    user_signup: UserSignupPM = Form(
        ...,
        title="User Signup Data",
        description="Form data to sign up the new user account.",
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Signing up user with '{user_signup.email}' email...")

    try:
        _base_url = get_base_url(request)
        await service.async_signup(
            async_session=db_session,
            user_signup=user_signup,
            base_url=_base_url,
            logger=_logger,
        )
        await db_session.commit()

        _logger.success(
            f"Successfully signed up user with '{user_signup.email}' email."
        )
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception(f"Failed to sign up user with '{user_signup.email}' email!")
        raise http_errors.InternalServerError(message="Failed to sign up user!")

    _response = BaseResponse(
        request=request,
        status_code=201,
        message="Registration successful, please check your email to verify your account.",
    )
    return _response


@router.post(
    "/resend-verification",
    summary="Resend Verification Mail",
    status_code=202,
    response_model=BaseResPM,
    responses={400: {}, 422: {}},
)
async def post_resend_verification(
    request: Request,
    email: EmailStr = Form(
        ...,
        title="Email",
        description="Email address to resend the verify url mail.",
        examples=["user@example.com"],
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Resending verification mail to '{email}' email...")

    _response = BaseResponse(
        request=request,
        status_code=202,
        message="Resent verification mail, if email is registered and not verified.",
    )

    try:
        _base_url = get_base_url(request)
        await service.async_resend_verification(
            async_session=db_session, email=email, base_url=_base_url, logger=_logger
        )
        await db_session.commit()

        _logger.success(f"Successfully resent verification mail to '{email}' email.")
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            if (200 <= err.status_code) and (err.status_code < 300):
                return _response
            raise

        _logger.exception(f"Failed to resend verification mail to '{email}' email!")
        raise http_errors.InternalServerError(
            message="Failed to resend verification mail!"
        )

    return _response


@router.post(
    "/verify",
    summary="Verify User",
    response_model=BaseResPM,
    responses={
        400: {},
        401: {
            "description": """Token has expired or invalid!

Error codes|Description
---|---
`401_01000`|Verify token is missing!
`401_01001`|Verify token is invalid!
`401_01002`|Verify token has expired!
""",
        },
        409: {"description": "User is already verified!"},
        422: {},
    },
)
async def post_verify(
    request: Request,
    verify_token: SecretStr = Body(
        ...,
        min_length=16,
        max_length=4096,
        title="Verify Token",
        description="Token to verify the user account.",
        examples=[
            (
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwia"
                "WF0IjoxNTE2MjM5MDIyfQ.t42p4AHef69Tyyi88U6-p0utZYYrg7mmCGhoAd7Zffs"
            )
        ],
        embed=True,
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    if not is_valid(val=verify_token.get_secret_value(), pattern=JWT_REGEX):
        raise http_errors.UnprocessableEntityError(message="Invalid verify token!")

    _logger: Logger = request.state.logger
    _logger.info("Verifying the user with token...")

    try:
        await service.async_verify(
            async_session=db_session, verify_token=verify_token, logger=_logger
        )
        await db_session.commit()

        _logger.success("Successfully verified the user with token.")
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception("Failed to verify the user with token!")
        raise http_errors.InternalServerError(
            message="Failed to verify the user with token!"
        )

    _response = BaseResponse(
        request=request,
        message="Successfully verified the user email and activated the account.",
    )
    return _response


__all__ = [
    "post_signup",
    "post_resend_verification",
    "post_verify",
]
