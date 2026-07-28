import asyncio
import secrets
from typing import cast

from pydantic import validate_call, EmailStr, SecretStr
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from aiosmtplib.errors import SMTPException
from jwt import ExpiredSignatureError, InvalidTokenError

from potato_util.constants import WarnEnum
from potato_util.dt import now_utc_dt

from api.core.exceptions import http as http_errors
from api.resources.user.schemas import UserStatusEnum
from api.resources.user.model import UserORM
from api.resources.user import service as user_service
from api.externals import mail
from api.logger import Logger, logger

from .. import utils as auth_utils
from ..schemas import UserSignupPM, TokenTypeHintEnum, JWTPayloadPM


@validate_call(config={"arbitrary_types_allowed": True})
async def async_signup(
    async_session: AsyncSession,
    user_signup: UserSignupPM,
    base_url: str,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> UserORM:
    """Sign up a new user."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Signing up user with '{user_signup.email}' email...")

    _user_orm = await user_service.async_get_by_email(
        async_session=async_session,
        email=user_signup.email,
        allow_no_result=True,
        logger=logger,
        warn_mode=WarnEnum.DEBUG,
    )

    if _user_orm:
        if _user_orm.status == UserStatusEnum.PENDING:
            raise http_errors.ConflictError(
                message=(
                    "User email already registered but account is not verified, please check your "
                    "email to verify it or make a request to resend verification email!"
                ),
            )

        if (_user_orm.status == UserStatusEnum.DISABLED) or (
            _user_orm.status == UserStatusEnum.DELETED
        ):
            logger.warning(
                f"[ANOMALY] - Attempting to signup with '{user_signup.email}' email but account "
                "is already disabled or deleted!"
            )
            raise http_errors.BadRequestError(
                message=(
                    "User email already registered but account is disabled or deleted, "
                    "please contact the support team to get help!\n"
                    "If account is deleted, it will be permanently deleted in 30 days!"
                ),
            )

        assert (
            _user_orm.status == UserStatusEnum.ACTIVE
        ), "Only 'ACTIVE' status is allowed after validations!"

        logger.warning(
            f"[ANOMALY] - Attempting to signup with '{user_signup.email}' email but account is already registered "
            "and active!"
        )
        raise http_errors.ConflictError(
            message="User email already registered!",
        )

    try:
        _user_dict = user_signup.model_dump(exclude={"password", "password_confirm"})
        _user_orm = await user_service.async_create(
            async_session=async_session,
            user_in={  # type: ignore
                **_user_dict,
                "status": UserStatusEnum.PENDING,
                "password": user_signup.password.get_secret_value(),
            },
            logger=logger,
            warn_mode=WarnEnum.DEBUG,
        )

        _jwt_payload = JWTPayloadPM(
            sub=_user_orm.id, typ=TokenTypeHintEnum.verify_token
        )
        _verify_token = auth_utils.gen_jwt(payload=_jwt_payload)

        _verify_url = auth_utils.make_verify_url(
            base_url=base_url, verify_token=_verify_token
        )

        logger.info(f"Sending verification email to '{user_signup.email}'...")
        await mail.async_send_verify(email=user_signup.email, verify_url=_verify_url)
        logger.success(
            f"Successfully sent verification email to '{user_signup.email}'."
        )
    except SMTPException:
        logger.exception(f"Failed to send verification email to '{user_signup.email}'!")
        raise http_errors.SMTPError(
            message="Failed to send verification email!",
        )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(
            f"Successfully signed up user with '{user_signup.email}' email and '{_user_orm.id}' ID."
        )

    return _user_orm


@validate_call(config={"arbitrary_types_allowed": True})
async def async_resend_verification(
    async_session: AsyncSession,
    email: EmailStr,
    base_url: str,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> None:
    """Resend verification mail to the user."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Resending verification mail to '{email}' email...")

    _user_orm = await user_service.async_get_by_email(
        async_session=async_session,
        email=email,
        allow_no_result=True,
        logger=logger,
        warn_mode=WarnEnum.DEBUG,
    )

    if not _user_orm:
        logger.warning(
            f"[ANOMALY] - Attempting to resend verification mail to '{email}' email but it's not registered!"
        )
        await asyncio.sleep(secrets.SystemRandom().uniform(1, 3))
        raise HTTPException(status_code=202)

    if _user_orm.status == UserStatusEnum.ACTIVE:
        logger.warning(
            f"[ANOMALY] - Attempting to resend verification mail to '{email}' email but it's already verified!"
        )
        await asyncio.sleep(secrets.SystemRandom().uniform(1, 3))
        raise HTTPException(status_code=202)

    if (_user_orm.status == UserStatusEnum.DISABLED) or (
        _user_orm.status == UserStatusEnum.DELETED
    ):
        logger.warning(
            f"[ANOMALY] - Attempting to resend verification mail to '{email}' email but account is disabled or "
            "deleted!"
        )
        await asyncio.sleep(secrets.SystemRandom().uniform(1, 3))
        raise http_errors.BadRequestError(
            message="User account is disabled or deleted, please contact the support team to get help!",
        )

    assert (
        _user_orm.status == UserStatusEnum.PENDING
    ), "Only 'PENDING' status is allowed for resending verification mail!"

    try:
        _jwt_payload = JWTPayloadPM(
            sub=_user_orm.id, typ=TokenTypeHintEnum.verify_token
        )
        _verify_token = await auth_utils.async_gen_jwt(payload=_jwt_payload)

        _verify_url = auth_utils.make_verify_url(
            base_url=base_url, verify_token=_verify_token
        )

        logger.info(f"Sending verification mail to '{email}'...")
        await mail.async_send_verify(email=email, verify_url=_verify_url)
        logger.success(f"Successfully sent verification mail to '{email}' email.")
    except SMTPException:
        logger.exception(f"Failed to send verification mail to '{email}' email!")
        raise http_errors.SMTPError(
            message="Failed to send verification mail!",
        )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully resent verification mail to '{email}' email.")

    return


@validate_call(config={"arbitrary_types_allowed": True})
async def async_verify(
    async_session: AsyncSession,
    verify_token: SecretStr,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> UserORM:
    """Verify the user account with the verify token."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug("Verifying user account with verify token...")

    try:
        _jwt_payload = cast(
            JWTPayloadPM,
            await auth_utils.async_verify_jwt(
                token=verify_token, jwt_type=TokenTypeHintEnum.verify_token
            ),
        )
    except ExpiredSignatureError:
        logger.warning(
            "[ANOMALY] - Attempting to verify user with expired verify token!"
        )
        raise http_errors.TokenExpiredError(
            message="Verify token has expired!",
        )
    except InvalidTokenError:
        logger.warning(
            "[ANOMALY] - Attempting to verify user with invalid verify token!"
        )
        raise http_errors.TokenInvalidError(
            message="Verify token is invalid!",
        )

    if _jwt_payload.typ != TokenTypeHintEnum.verify_token:
        logger.warning(
            f"[ANOMALY] - Attempting to verify user with invalid verify token '{_jwt_payload.typ}' type!"
        )
        raise http_errors.TokenInvalidError(
            message="Verify token is invalid!",
        )

    _user_id = _jwt_payload.sub
    _user_orm = await user_service.async_get(
        async_session=async_session,
        id_=_user_id,
        allow_no_result=True,
        logger=logger,
        warn_mode=WarnEnum.DEBUG,
    )

    if not _user_orm:
        logger.warning(
            "[ANOMALY] - Attempting to verify user with valid verify token but user is not found from the database!"
        )
        raise http_errors.TokenInvalidError(
            message="Verify token is invalid!",
        )

    if _user_orm.status == UserStatusEnum.ACTIVE:
        logger.warning(
            "[ANOMALY] - Attempting to verify user with valid verify token but user is already verified!"
        )
        raise http_errors.ConflictError(
            message="User account is already verified!",
        )

    if (_user_orm.status == UserStatusEnum.DISABLED) or (
        _user_orm.status == UserStatusEnum.DELETED
    ):
        logger.warning(
            "[ANOMALY] - Attempting to verify user with valid verify token but user is disabled or deleted!"
        )
        raise http_errors.BadRequestError(
            message="User account is disabled or deleted!",
        )

    assert (
        _user_orm.status == UserStatusEnum.PENDING
    ), "Only 'PENDING' status is allowed for verifying user account!"

    _user_orm.verified_at = now_utc_dt()
    _user_orm.status = UserStatusEnum.ACTIVE

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(
            f"Successfully verified user with '{_user_orm.email}' email and '{_user_orm.id}' ID."
        )

    return _user_orm


__all__ = [
    "async_signup",
    "async_resend_verification",
    "async_verify",
]
