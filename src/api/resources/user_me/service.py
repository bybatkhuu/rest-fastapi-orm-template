from typing import cast
from collections.abc import Collection

from pydantic import validate_call, SecretStr
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from potato_util.constants import WarnEnum
from potato_util.dt import now_utc_dt
from potato_util.crypto import password as password_utils

from api.core.exceptions import http as http_errors
from api.externals.db.models.exceptions import NullConstraintError, EmptyValueError
from api.resources.user.schemas import UserStatusEnum
from api.resources.user.model import UserORM
from api.resources.user import service as user_service
from api.resources.user_token import service as user_token_service
from api.config import config
from api.logger import Logger, logger

from .schemas import UserMeUpPM, UserMeChangePasswordPM


@validate_call(config={"arbitrary_types_allowed": True})
async def async_get_me(
    async_session: AsyncSession,
    id_: str,
    joins: Collection[str] | list[str] | set[str] | None = None,
    allow_no_result: bool = False,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> UserORM | None:
    """Get my account info."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Getting user ('{id_}' ID) info...")

    _user_orm: UserORM | None = None
    try:
        _user_orm = cast(
            UserORM | None,
            await UserORM.async_get(
                async_session=async_session,
                id=id_,
                joins=joins,
                allow_no_result=allow_no_result,
            ),
        )
    except NoResultFound:
        raise http_errors.NotFoundError(
            message=f"Not found your account ({id_}' ID) info!"
        )

    if _user_orm and (warn_mode == WarnEnum.DEBUG):
        logger.debug(f"Successfully retrieved user ('{id_}' ID) info.")

    return _user_orm


@validate_call(config={"arbitrary_types_allowed": True})
async def async_update_me(
    async_session: AsyncSession,
    id_: str,
    user_up: UserMeUpPM,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> UserORM:
    """Update my account info."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Updating user ('{id_}' ID) info...")

    _user_orm: UserORM
    try:
        _user_orm = cast(
            UserORM,
            await UserORM.async_update_by_id(
                async_session=async_session,
                id=id_,
                **user_up.model_dump(exclude_unset=True),
            ),
        )
        await _user_orm.awaitable_attrs.roles
    except EmptyValueError:
        raise http_errors.UnprocessableEntityError(
            message="No user data provided to update!"
        )
    except NoResultFound:
        raise http_errors.NotFoundError(
            message=f"Not found your account ('{id_}' ID) to update!"
        )
    except NullConstraintError as err:
        raise http_errors.UnprocessableEntityError(
            message="Required user data is NULL!", description=f"User: {err}"
        )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully updated user ('{id_}' ID) info.")

    return _user_orm


@validate_call(config={"arbitrary_types_allowed": True})
async def async_change_my_password(
    async_session: AsyncSession,
    id_: str,
    user_change_password: UserMeChangePasswordPM,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> None:
    """Change user current password with new password."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(
            f"Changing user ('{id_}' ID) current password with new password..."
        )

    _user_orm = cast(
        UserORM | None,
        await UserORM.async_get(
            async_session=async_session, id=id_, allow_no_result=True
        ),
    )

    if not _user_orm:
        raise http_errors.NotFoundError(
            message=f"Not found your account ('{id_}' ID) to change current password!"
        )

    if not password_utils.verify(
        hashed_password=_user_orm.password_hash,
        password=user_change_password.current_password,
        password_pepper=config.api.security.password.pepper,
    ):
        raise http_errors.UnauthorizedError(message="Current password is incorrect!")

    if _user_orm.status != UserStatusEnum.ACTIVE:
        raise http_errors.ForbiddenError(message="Your account is disabled or deleted!")

    await user_service.async_update_password(
        async_session=async_session,
        id_=id_,
        password=user_change_password.password,
        logger=logger,
        warn_mode=WarnEnum.DEBUG,
    )

    if user_change_password.logout_all:
        await user_token_service.async_revoke_refresh_tokens(
            async_session=async_session,
            user_id=id_,
            logger=logger,
            warn_mode=WarnEnum.DEBUG,
        )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(
            f"Successfully changed user ('{id_}' ID) current password with new password."
        )

    return


@validate_call(config={"arbitrary_types_allowed": True})
async def async_delete_me(
    async_session: AsyncSession,
    id_: str,
    password: SecretStr,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> None:
    """Delete my account."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Deleting user ('{id_}' ID) account...")

    try:
        _user_orm = cast(
            UserORM, await UserORM.async_get(async_session=async_session, id=id_)
        )

        if not password_utils.verify(
            hashed_password=_user_orm.password_hash,
            password=password,
            password_pepper=config.api.security.password.pepper,
        ):
            raise http_errors.UnauthorizedError(message="Password is incorrect!")

        if _user_orm.status != UserStatusEnum.ACTIVE:
            raise http_errors.ForbiddenError(
                message="Your account is disabled or deleted!"
            )

        if _user_orm.protected:
            raise http_errors.UnprocessableEntityError(
                message="Your account is protected and cannot be deleted!"
            )

        _user_orm.status = UserStatusEnum.DELETED
        _user_orm.deleted_at = now_utc_dt()
    except NoResultFound:
        raise http_errors.NotFoundError(
            message=f"Not found your account ('{id_}' ID) to delete!"
        )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully deleted user ('{id_}' ID) account.")

    return


__all__ = [
    "async_get_me",
    "async_update_me",
    "async_change_my_password",
    "async_delete_me",
]
