import asyncio
import secrets
from typing import cast
from ipaddress import IPv4Address, IPv6Address

from pydantic import validate_call, EmailStr
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from aiosmtplib.errors import SMTPException
from jwt import ExpiredSignatureError, InvalidTokenError

from potato_util.constants import WarnEnum
from potato_util.dt import now_utc_dt, calc_future_dt

from api.core.exceptions import http as http_errors
from api.resources.user.schemas import UserStatusEnum
from api.resources.user.model import UserORM
from api.resources.user import service as user_service
from api.resources.user_token import service as user_token_service
from api.resources.user_token.schemas import UserTokenKindEnum, UserTokenStatusEnum
from api.externals import mail
from api.config import config
from api.logger import Logger, logger

from .. import utils as auth_utils
from ..schemas import UserResetPasswordPM, TokenTypeHintEnum, SecretTokenPayloadPM


@validate_call(config={"arbitrary_types_allowed": True})
async def async_forgot_password(
    async_session: AsyncSession,
    email: EmailStr,
    base_url: str,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> None:
    """Forgot password for a user."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Forgot password for user with '{email}' email...")

    _user_orm = await user_service.async_get_by_email(
        async_session=async_session,
        email=email,
        allow_no_result=True,
        logger=logger,
        warn_mode=WarnEnum.DEBUG,
    )

    if not _user_orm:
        logger.warning(
            f"[ANOMALY] - Attempting to send reset password mail to '{email}' email but it's not registered!"
        )
        await asyncio.sleep(secrets.SystemRandom().uniform(1, 3))
        raise HTTPException(status_code=202)

    if _user_orm.status == UserStatusEnum.PENDING:
        logger.warning(
            f"[ANOMALY] - Attempting to send reset password mail to '{email}' email but account is not verified yet!"
        )
        await asyncio.sleep(secrets.SystemRandom().uniform(1, 3))
        raise http_errors.NotVerifiedError(
            message="User account is not verified yet, please check your email to verify it or make a new request to "
            "resend verification email!"
        )

    if (_user_orm.status == UserStatusEnum.DISABLED) or (
        _user_orm.status == UserStatusEnum.DELETED
    ):
        logger.warning(
            f"[ANOMALY] - Attempting to send reset password mail to '{email}' email but account is disabled or "
            "deleted!"
        )
        await asyncio.sleep(secrets.SystemRandom().uniform(1, 3))
        raise http_errors.BadRequestError(
            message="User account is disabled or deleted, please contact the support team to get help!"
        )

    assert (
        _user_orm.status == UserStatusEnum.ACTIVE
    ), "Only 'ACTIVE' status is allowed for sending reset password mail!"

    try:
        _issued_at = now_utc_dt()
        _reset_expires_at = calc_future_dt(
            dt=_issued_at, delta=config.api.security.token.reset_duration
        )
        _reset_secret, _reset_token_orm = await user_token_service.async_generate(
            async_session=async_session,
            user_id=_user_orm.id,
            kind=UserTokenKindEnum.RESET,
            expires_at=_reset_expires_at,
            logger=logger,
            warn_mode=WarnEnum.DEBUG,
        )
        _jwt_payload = SecretTokenPayloadPM(
            sub=_user_orm.id,
            exp=_reset_expires_at,
            iat=_issued_at,
            jti=_reset_token_orm.id,
            typ=TokenTypeHintEnum.reset_token,
            token=_reset_secret,
        )
        _reset_token = await auth_utils.async_gen_jwt(payload=_jwt_payload)

        _reset_password_url = auth_utils.make_reset_password_url(
            base_url=base_url, reset_token=_reset_token
        )

        logger.info(f"Sending reset password mail to '{email}'...")
        await mail.async_send_reset_password(
            email=email, reset_password_url=_reset_password_url
        )
        logger.success(f"Successfully sent reset password mail to '{email}' email.")
    except SMTPException:
        logger.exception(f"Failed to send reset password mail to '{email}'!")
        raise http_errors.SMTPError(message="Failed to send reset password mail!")

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully sent reset password mail to '{email}' email.")

    return


@validate_call(config={"arbitrary_types_allowed": True})
async def async_reset_password(
    async_session: AsyncSession,
    user_reset_password: UserResetPasswordPM,
    client_host: IPv4Address | IPv6Address,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> UserORM:
    """Reset the user password with new password and reset token."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug("Resetting the user password with new password and reset token...")

    try:
        _jwt_payload = cast(
            SecretTokenPayloadPM,
            await auth_utils.async_verify_jwt(
                token=user_reset_password.reset_token,
                jwt_type=TokenTypeHintEnum.reset_token,
            ),
        )
    except ExpiredSignatureError:
        logger.warning(
            "[ANOMALY] - Attempting to reset user password but reset token has expired!"
        )
        raise http_errors.TokenExpiredError(message="Reset token has expired!")
    except InvalidTokenError:
        logger.warning(
            "[ANOMALY] - Attempting to reset user password but reset token is invalid!"
        )
        raise http_errors.TokenInvalidError(message="Reset token is invalid!")

    _user_id = _jwt_payload.sub
    _token_secret = _jwt_payload.token
    _user_token_orm = await user_token_service.async_get_by_token(
        async_session=async_session,
        token=_token_secret,
        user_id=_user_id,
        kind=UserTokenKindEnum.RESET,
        joins=["user"],
        logger=logger,
        warn_mode=WarnEnum.DEBUG,
    )

    if not _user_token_orm:
        logger.warning(
            "[ANOMALY] - Attempting to reset user password with valid reset token but user reset token is not "
            "found from the database!"
        )
        raise http_errors.TokenInvalidError(message="Reset token is invalid!")

    if _user_token_orm.status == UserTokenStatusEnum.USED:
        logger.warning(
            "[TOKEN_REUSE_DETECTED] - Attempting to reset user password with valid reset token but user "
            f"'{_user_id}' ID's reset token is already used!"
        )
        raise http_errors.TokenInvalidError(message="Invalid reset token!")

    _current_dt = now_utc_dt()
    if (_user_token_orm.status == UserTokenStatusEnum.EXPIRED) or (
        _user_token_orm.expires_at < _current_dt
    ):
        logger.warning(
            "[ANOMALY] - Attempting to reset user password with expired reset token!"
        )
        raise http_errors.TokenExpiredError(message="Reset token has expired!")

    if (_user_token_orm.status == UserTokenStatusEnum.REVOKED) or (
        _user_token_orm.status == UserTokenStatusEnum.BLOCKED
    ):
        logger.warning(
            "[ANOMALY] - Attempting to reset user password with revoked or blocked reset token!"
        )
        raise http_errors.TokenInvalidError(message="Invalid reset token!")

    assert (
        _user_token_orm.status == UserTokenStatusEnum.ACTIVE
    ), "Only 'ACTIVE' status is allowed for resetting user password!"

    _user_orm: UserORM = _user_token_orm.user
    if _user_orm.status != UserStatusEnum.ACTIVE:
        logger.warning(
            f"[ANOMALY] - Attempting to reset user password with valid reset token but user "
            f"'{_user_id}' ID's account is not ACTIVE!"
        )
        raise http_errors.ForbiddenError(message="User account is not active!")

    await user_service.async_update_password(
        async_session=async_session,
        id_=_user_id,
        password=user_reset_password.password,
        logger=logger,
        warn_mode=WarnEnum.DEBUG,
    )

    if user_reset_password.logout_all:
        await user_token_service.async_revoke_refresh_tokens(
            async_session=async_session,
            user_id=_user_id,
            logger=logger,
            warn_mode=WarnEnum.DEBUG,
        )

    _user_token_orm.used_ip = client_host
    _user_token_orm.used_at = _current_dt
    _user_token_orm.status = UserTokenStatusEnum.USED

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully reset password of the user with '{_user_id}' ID.")

    return _user_orm


__all__ = [
    "async_forgot_password",
    "async_reset_password",
]
