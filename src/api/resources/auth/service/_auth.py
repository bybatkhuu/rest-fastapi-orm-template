import asyncio
import secrets
from typing import cast
from datetime import datetime
from ipaddress import IPv4Address, IPv6Address

from pydantic import validate_call, SecretStr
from sqlalchemy.ext.asyncio import AsyncSession
from jwt import ExpiredSignatureError, InvalidTokenError

from potato_util.constants import WarnEnum
from potato_util.dt import now_utc_dt, calc_future_dt
from potato_util.crypto import password as password_utils

from api.core.exceptions import http as http_errors
from api.resources.user.schemas import UserStatusEnum
from api.resources.user.model import UserORM
from api.resources.user import service as user_service
from api.resources.user_token.schemas import UserTokenKindEnum, UserTokenStatusEnum
from api.resources.user_token import service as user_token_service
from api.config import config
from api.logger import Logger, logger

from .. import utils as auth_utils
from ..schemas import (
    UserLoginPM,
    TokenTypeHintEnum,
    SecretTokenPayloadPM,
    AccessTokenPayloadPM,
    AuthTokensOutPM,
    TokenRevokeTypeEnum,
)


@validate_call(config={"arbitrary_types_allowed": True})
async def async_login(
    async_session: AsyncSession,
    user_login: UserLoginPM,
    client_host: IPv4Address | IPv6Address,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> tuple[AuthTokensOutPM, datetime]:
    """Authenticate the user and issue tokens."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(
            f"Authenticating user with '{user_login.email}' email and password..."
        )

    _user_orm = await user_service.async_get_by_email(
        async_session=async_session,
        logger=logger,
        email=user_login.email,
        joins=["roles"],
        allow_no_result=True,
        warn_mode=WarnEnum.DEBUG,
    )

    if not _user_orm:
        logger.warning(
            f"[ANOMALY] - Attempting to authenticate user with '{user_login.email}' email but it's not registered!"
        )
        await asyncio.sleep(
            secrets.SystemRandom().uniform(0, 1)
        )  # To prevent timing and brute-force attacks
        raise http_errors.UnauthorizedError(message="Incorrect email or password!")

    if not password_utils.verify(
        hashed_password=_user_orm.password_hash,
        password=user_login.password,
        password_pepper=config.api.security.password.pepper,
    ):
        logger.warning(
            f"[ANOMALY] - Attempting to authenticate user with '{user_login.email}' email but password is incorrect!"
        )
        raise http_errors.UnauthorizedError(message="Incorrect email or password!")

    if _user_orm.status == UserStatusEnum.PENDING:
        logger.warning(
            f"[ANOMALY] - Attempting to authenticate user with '{user_login.email}' email but account is "
            "not verified!"
        )
        raise http_errors.NotVerifiedError(message="User account is not verified!")

    if (_user_orm.status == UserStatusEnum.DISABLED) or (
        _user_orm.status == UserStatusEnum.DELETED
    ):
        logger.warning(
            f"[ANOMALY] - Attempting to authenticate user with '{user_login.email}' email but it's disabled or "
            "deleted!"
        )
        raise http_errors.ForbiddenError(message="User account is disabled or deleted!")

    assert (
        _user_orm.status == UserStatusEnum.ACTIVE
    ), "Only 'ACTIVE' status is allowed for authenticating user!"

    # Resolving user roles and scopes
    _roles, _scopes = await _user_orm.async_get_permissions()

    # Issuing access token
    _issued_at = now_utc_dt()
    _access_payload_pm = AccessTokenPayloadPM(
        sub=_user_orm.id,
        iat=_issued_at,
        nickname=_user_orm.nickname,
        email=_user_orm.email,
        email_verified=True,
        roles=_roles,
        scopes=_scopes,
        timezone=_user_orm.timezone,  # type: ignore
    )
    _access_token = auth_utils.gen_jwt(payload=_access_payload_pm)

    # Issuing refresh token
    _refresh_duration = config.api.security.token.refresh_duration
    if user_login.remember_me:
        _refresh_duration = config.api.security.token.remember_duration

    _refresh_expires_at = calc_future_dt(dt=_issued_at, delta=_refresh_duration)
    _refresh_secret, _refresh_token_orm = await user_token_service.async_generate(
        async_session=async_session,
        user_id=_user_orm.id,
        kind=UserTokenKindEnum.REFRESH,
        expires_at=_refresh_expires_at,
        logger=logger,
        warn_mode=WarnEnum.DEBUG,
    )
    _refresh_payload_pm = SecretTokenPayloadPM(
        sub=_user_orm.id,
        exp=_refresh_expires_at,
        iat=_issued_at,
        jti=_refresh_token_orm.id,
        typ=TokenTypeHintEnum.refresh_token,
        token=_refresh_secret,
        ati=_access_payload_pm.jti,  # type: ignore
    )
    _refresh_token = await auth_utils.async_gen_jwt(payload=_refresh_payload_pm)

    # Updating user last login details
    _user_orm.last_login_ip = client_host
    _user_orm.last_login_at = _issued_at

    assert _access_payload_pm.exp, "Pydantic model validator should've filled `exp`!"
    _auth_tokens_pm = AuthTokensOutPM(
        access_token=_access_token.get_secret_value(),
        scopes=_scopes,
        refresh_token=_refresh_token.get_secret_value(),
    )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(
            f"Successfully authenticated user with '{user_login.email}' email and issued tokens."
        )

    return _auth_tokens_pm, _refresh_expires_at


@validate_call(config={"arbitrary_types_allowed": True})
async def async_refresh(
    async_session: AsyncSession,
    refresh_token: SecretStr,
    client_host: IPv4Address | IPv6Address,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> tuple[AuthTokensOutPM, datetime]:
    """Refresh tokens."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug("Refreshing tokens...")

    try:
        _jwt_payload = cast(
            SecretTokenPayloadPM,
            await auth_utils.async_verify_jwt(
                token=refresh_token, jwt_type=TokenTypeHintEnum.refresh_token
            ),
        )
    except ExpiredSignatureError:
        logger.warning(
            "[ANOMALY] - Attempting to refresh tokens with expired refresh token!"
        )
        raise http_errors.TokenExpiredError(message="Refresh token has expired!")
    except InvalidTokenError:
        logger.warning(
            "[ANOMALY] - Attempting to refresh tokens with invalid refresh token!"
        )
        raise http_errors.TokenInvalidError(message="Invalid refresh token!")

    _user_id = _jwt_payload.sub
    _token_secret = _jwt_payload.token
    _user_token_orm = await user_token_service.async_get_by_token(
        async_session=async_session,
        token=_token_secret,
        user_id=_user_id,
        kind=UserTokenKindEnum.REFRESH,
        joins=["user"],
        logger=logger,
        warn_mode=WarnEnum.DEBUG,
    )

    if not _user_token_orm:
        logger.warning(
            f"[ANOMALY] - Attempting to refresh tokens with valid refresh token but not found '{_user_id}' user "
            "refresh token from the database!"
        )
        raise http_errors.TokenInvalidError(message="Invalid refresh token!")

    assert (
        _user_token_orm.family_token_id
    ), "All refresh tokens must have a family token ID!"

    if _user_token_orm.status == UserTokenStatusEnum.USED:
        logger.warning(
            f"[TOKEN_THEFT_DETECTED] - Attempting to refresh tokens with valid refresh token but user '{_user_id}' "
            "ID's refresh token is already used!"
        )
        await user_token_service.async_block_refresh_tokens(
            async_session=async_session,
            family_token_id=_user_token_orm.family_token_id,
            logger=logger,
            warn_mode=WarnEnum.DEBUG,
        )
        await async_session.commit()
        raise http_errors.TokenInvalidError(message="Invalid refresh token!")

    _resfresh_expires_at = _user_token_orm.expires_at
    _current_dt = now_utc_dt()
    if (_user_token_orm.status == UserTokenStatusEnum.EXPIRED) or (
        _resfresh_expires_at < _current_dt
    ):
        logger.warning(
            "[ANOMALY] - Attempting to refresh tokens with expired refresh token!"
        )
        raise http_errors.TokenExpiredError(message="Refresh token has expired!")

    if (_user_token_orm.status == UserTokenStatusEnum.REVOKED) or (
        _user_token_orm.status == UserTokenStatusEnum.BLOCKED
    ):
        logger.warning(
            "[ANOMALY] - Attempting to refresh tokens with revoked or blocked refresh token!"
        )
        raise http_errors.TokenInvalidError(message="Invalid refresh token!")

    assert (
        _user_token_orm.status == UserTokenStatusEnum.ACTIVE
    ), "Only 'ACTIVE' status is allowed for refreshing tokens!"

    _user_orm: UserORM = _user_token_orm.user
    if _user_orm.status != UserStatusEnum.ACTIVE:
        logger.warning(
            f"[ANOMALY] - Attempting to refresh tokens with valid refresh token but user '{_user_id}' ID's account "
            "is not ACTIVE!"
        )
        raise http_errors.ForbiddenError(message="User account is not active!")

    # Resolving user roles and scopes
    _roles, _scopes = await _user_orm.async_get_permissions()

    # Issuing access token
    _issued_at = now_utc_dt()
    _access_payload_pm = AccessTokenPayloadPM(
        sub=_user_orm.id,
        iat=_issued_at,
        nickname=_user_orm.nickname,
        email=_user_orm.email,
        email_verified=True,
        roles=_roles,
        scopes=_scopes,
        timezone=_user_orm.timezone,  # type: ignore
    )
    _access_token = auth_utils.gen_jwt(payload=_access_payload_pm)

    # Issuing refresh token
    _refresh_secret, _refresh_token_orm = await user_token_service.async_generate(
        async_session=async_session,
        user_id=_user_orm.id,
        kind=UserTokenKindEnum.REFRESH,
        expires_at=_resfresh_expires_at,
        family_token_id=_user_token_orm.family_token_id,
        logger=logger,
        warn_mode=WarnEnum.DEBUG,
    )
    _refresh_payload_pm = SecretTokenPayloadPM(
        sub=_user_orm.id,
        exp=_resfresh_expires_at,
        iat=_issued_at,
        jti=_refresh_token_orm.id,
        typ=TokenTypeHintEnum.refresh_token,
        token=_refresh_secret,
        ati=_access_payload_pm.jti,  # type: ignore
    )
    _refresh_token = await auth_utils.async_gen_jwt(payload=_refresh_payload_pm)

    _user_token_orm.used_ip = client_host
    _user_token_orm.used_at = _current_dt
    _user_token_orm.status = UserTokenStatusEnum.USED

    assert _access_payload_pm.exp, "Pydantic model validator should've filled `exp`!"
    _auth_tokens_pm = AuthTokensOutPM(
        access_token=_access_token.get_secret_value(),
        scopes=_scopes,
        refresh_token=_refresh_token.get_secret_value(),
    )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug("Successfully refreshed tokens.")

    return _auth_tokens_pm, _resfresh_expires_at


@validate_call(config={"arbitrary_types_allowed": True})
async def async_revoke(
    async_session: AsyncSession,
    token: SecretStr,
    token_type_hint: TokenRevokeTypeEnum,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> None:
    """Revoke token."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Revoking '{token_type_hint.value}' type token...")

    try:
        _jwt_payload = cast(
            SecretTokenPayloadPM,
            await auth_utils.async_verify_jwt(
                token=token, jwt_type=token_type_hint, verify_exp=False
            ),
        )
    except InvalidTokenError:
        logger.warning("[ANOMALY] - Attempting to revoke token with invalid token!")
        raise http_errors.TokenInvalidError(message="Invalid token!")

    _user_id = _jwt_payload.sub
    _token_secret = _jwt_payload.token
    _kind = UserTokenKindEnum(token_type_hint.value.replace("_token", "").upper())
    _user_token_orm = await user_token_service.async_get_by_token(
        async_session=async_session,
        logger=logger,
        token=_token_secret,
        user_id=_user_id,
        kind=_kind,
        warn_mode=WarnEnum.DEBUG,
    )

    if not _user_token_orm:
        logger.warning(
            f"[ANOMALY] - Attempting to revoke token with valid token but not found '{_user_id}' user token "
            "from the database!"
        )
        raise http_errors.TokenInvalidError(message="Invalid token!")

    if _user_token_orm.status != UserTokenStatusEnum.ACTIVE:
        logger.warning(
            f"[ANOMALY] - Attempting to revoke token with valid token but user '{_user_id}' ID's token "
            "is not ACTIVE!"
        )
        raise http_errors.TokenInvalidError(message="Invalid token!")

    _user_token_orm.status = UserTokenStatusEnum.REVOKED
    _user_token_orm.revoked_at = now_utc_dt()

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully revoked '{token_type_hint.value}' type token.")

    return


__all__ = [
    "async_login",
    "async_refresh",
    "async_revoke",
]
