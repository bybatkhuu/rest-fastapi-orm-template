from typing import cast
from collections.abc import Collection

from pydantic import validate_call, EmailStr, SecretStr
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from potato_util.constants import WarnEnum
from potato_util.dt import now_utc_dt
from potato_util import io as io_utils
from potato_util.crypto import password as password_utils

from api.core.exceptions import http as http_errors
from api.externals.db.models.exceptions import (
    NullConstraintError,
    EmptyValueError,
    UniqueKeyError,
)
from api.resources.table_stat import service as table_stat_service
from api.resources.role.schemas import RoleSourceEnum
from api.resources.role.model import RoleORM
from api.resources.role import service as role_service
from api.resources.user_token import service as user_token_service
from api.config import config
from api.logger import Logger, logger

from .schemas import UserInPM, UserUpPM, UserStatusEnum
from .model import UserORM


@validate_call(config={"arbitrary_types_allowed": True})
async def async_get_list(
    async_session: AsyncSession,
    offset: int = 0,
    limit: int = config.db.select_limit,
    is_desc: bool = config.db.select_is_desc,
    order_by: Collection[str] | list[str] | set[str] | str | None = None,
    joins: Collection[str] | list[str] | set[str] | None = None,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
    **kwargs,
) -> tuple[list[UserORM], int]:
    """Get list of user and total count."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug("Getting user list...")

    _where = []
    if kwargs:
        for _key, _val in kwargs.items():
            _where.append({"column": _key, "op": "like", "value": _val})

    _user_orms = cast(
        list[UserORM],
        await UserORM.async_select_by_where(
            async_session=async_session,
            where=_where,
            offset=offset,
            limit=limit,
            is_desc=is_desc,
            order_by=order_by,
            joins=joins,
        ),
    )

    _total_count = 0
    if _where:
        _total_count = await UserORM.async_count_by_where(
            async_session=async_session, where=_where
        )
    else:
        _total_count = await table_stat_service.async_get_row_count(
            async_session=async_session,
            table_name=UserORM.__tablename__,
            logger=logger,
            warn_mode=WarnEnum.DEBUG,
        )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug("Successfully retrieved user list.")

    return _user_orms, _total_count


@validate_call(config={"arbitrary_types_allowed": True})
async def async_create(
    async_session: AsyncSession,
    user_in: UserInPM,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> UserORM:
    """Create a new user."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Creating user with '{user_in.email}' email...")

    _user_orm: UserORM
    _user_dir: str | None = None
    try:
        assert user_in.password, "Password will be generated automatically!"
        _user_dict = user_in.model_dump(exclude={"password", "roles"})
        _user_dict["password_hash"] = password_utils.hash(
            password=user_in.password,
            password_pepper=config.api.security.password.pepper,
        )

        if user_in.status == UserStatusEnum.ACTIVE:
            _user_dict["verified_at"] = now_utc_dt()

        _user_orm = cast(
            UserORM,
            await UserORM.async_insert(async_session=async_session, **_user_dict),
        )

        _role_orms: list[RoleORM] = []
        for _role in user_in.roles:
            _role_orm = cast(
                RoleORM,
                await role_service.async_get(
                    async_session=async_session,
                    name=_role,
                    allow_no_result=True,
                    logger=logger,
                    warn_mode=WarnEnum.DEBUG,
                ),
            )

            if not _role_orm:
                raise http_errors.UnprocessableEntityError(
                    message=f"Role '{_role}' name does not exist!"
                )

            if _role_orm.source != RoleSourceEnum.INTERNAL:
                raise http_errors.UnprocessableEntityError(
                    message="Only internal roles can be assigned to users!",
                    description=f"Role: {_role_orm.name}",
                )

            _role_orms.append(_role_orm)

        await _user_orm.awaitable_attrs.roles
        if _role_orms:
            _user_orm.roles = _role_orms

        _user_dir = config.api.paths.user_dir.format(user_id=_user_orm.id)
        await io_utils.async_create_dir(_user_dir)
    except Exception as err:
        if _user_dir:
            await io_utils.async_remove_dir(_user_dir)

        if isinstance(err, NullConstraintError):
            raise http_errors.UnprocessableEntityError(
                message="Required user data is missing!", description=f"User: {err}"
            )
        if isinstance(err, UniqueKeyError):
            raise http_errors.ConflictError(
                message="User email already exists!", description=f"User: {err}"
            )

        raise

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(
            f" Successfully created user with '{user_in.email}' email and '{_user_orm.id}' ID."
        )

    return _user_orm


@validate_call(config={"arbitrary_types_allowed": True})
async def async_get(
    async_session: AsyncSession,
    id_: str,
    joins: Collection[str] | list[str] | set[str] | None = None,
    allow_no_result: bool = False,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> UserORM | None:
    """Get user by ID."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Getting user '{id_}' ID...")

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
        raise http_errors.NotFoundError(message=f"Not found any user '{id_}' ID!")

    if _user_orm and (warn_mode == WarnEnum.DEBUG):
        logger.debug(f"Successfully retrieved user '{id_}' ID.")

    return _user_orm


@validate_call(config={"arbitrary_types_allowed": True})
async def async_update(
    async_session: AsyncSession,
    id_: str,
    user_up: UserUpPM,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> UserORM:
    """Update user by ID."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Updating user '{id_}' ID...")

    _user_orm: UserORM
    try:
        _user_orm = cast(
            UserORM, await UserORM.async_get(async_session=async_session, id=id_)
        )

        _roles_up: set[str] = set[str]()
        _user_up_dict = user_up.model_dump(exclude_unset=True)
        if "roles" in _user_up_dict:
            _roles_up = _user_up_dict.pop("roles", set[str]())

        if _user_orm.protected and _roles_up:
            raise http_errors.UnprocessableEntityError(
                message="User is protected and cannot change roles!"
            )

        _role_orms: list[RoleORM] = []
        for _role_up in _roles_up:
            _role_orm = cast(
                RoleORM,
                await role_service.async_get(
                    async_session=async_session,
                    name=_role_up,
                    allow_no_result=True,
                    logger=logger,
                    warn_mode=WarnEnum.DEBUG,
                ),
            )

            if not _role_orm:
                raise http_errors.UnprocessableEntityError(
                    message=f"Role '{_role_up}' name does not exist!"
                )

            if _role_orm.source != RoleSourceEnum.INTERNAL:
                raise http_errors.UnprocessableEntityError(
                    message="Only internal roles can be assigned to users!",
                    description=f"Role: {_role_orm.name}",
                )

            _role_orms.append(_role_orm)

        await _user_orm.awaitable_attrs.roles
        if _role_orms:
            _user_up_dict["roles"] = _role_orms

        await _user_orm.async_update(async_session=async_session, **_user_up_dict)
    except EmptyValueError:
        raise http_errors.UnprocessableEntityError(
            message="No user data provided to update!"
        )
    except NoResultFound:
        raise http_errors.NotFoundError(message=f"Not found any user '{id_}' ID!")
    except NullConstraintError as err:
        raise http_errors.UnprocessableEntityError(
            message="Required user data is NULL!", description=f"User: {err}"
        )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully updated user '{id_}' ID.")

    return _user_orm


@validate_call(config={"arbitrary_types_allowed": True})
async def async_delete(
    async_session: AsyncSession,
    id_: str,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> None:
    """Delete user by ID."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Deleting user '{id_}' ID...")

    try:
        _user_orm = cast(
            UserORM, await UserORM.async_get(async_session=async_session, id=id_)
        )

        if _user_orm.protected:
            raise http_errors.UnprocessableEntityError(
                message="User is protected and cannot be deleted!"
            )

        await _user_orm.async_delete(async_session=async_session)
        _user_dir = config.api.paths.user_dir.format(user_id=id_)
        await io_utils.async_remove_dir(_user_dir)
    except NoResultFound:
        raise http_errors.NotFoundError(message=f"Not found any user '{id_}' ID!")

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully deleted user '{id_}' ID.")

    return


@validate_call(config={"arbitrary_types_allowed": True})
async def async_update_status(
    async_session: AsyncSession,
    id_: str,
    status: UserStatusEnum,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> None:
    """Update user status by ID."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Updating status of user '{id_}' ID...")

    try:
        _user_orm = cast(
            UserORM, await UserORM.async_get(async_session=async_session, id=id_)
        )

        if _user_orm.protected and (status == UserStatusEnum.DISABLED):
            raise http_errors.UnprocessableEntityError(
                message="User is protected and cannot be disabled!"
            )

        _user_orm.status = status
        if (status == UserStatusEnum.ACTIVE) and (not _user_orm.verified_at):
            _user_orm.verified_at = now_utc_dt()

    except NoResultFound:
        raise http_errors.NotFoundError(message=f"Not found any user '{id_}' ID!")

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully updated status of user '{id_}' ID.")

    return


@validate_call(config={"arbitrary_types_allowed": True})
async def async_update_password(
    async_session: AsyncSession,
    id_: str,
    password: SecretStr,
    logout_all: bool = False,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> None:
    """Update user password by ID."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Updating password of user '{id_}' ID...")

    try:
        _password_hash = password_utils.hash(
            password=password,
            password_pepper=config.api.security.password.pepper,
        )
        await UserORM.async_update_by_id(
            async_session=async_session,
            id=id_,
            password_hash=_password_hash,
            returning=False,
        )

        if logout_all:
            await user_token_service.async_revoke_refresh_tokens(
                async_session=async_session,
                user_id=id_,
                logger=logger,
                warn_mode=WarnEnum.DEBUG,
            )

    except NoResultFound:
        raise http_errors.NotFoundError(
            message=f"Not found any user '{id_}' ID to update password!"
        )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully updated password of user '{id_}' ID.")

    return


@validate_call(config={"arbitrary_types_allowed": True})
async def async_update_protected(
    async_session: AsyncSession,
    id_: str,
    protected: bool,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> None:
    """Update protected flag of user by ID."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Updating protected flag of user '{id_}' ID...")

    try:
        await UserORM.async_update_by_id(
            async_session=async_session, id=id_, returning=False, protected=protected
        )
    except NoResultFound:
        raise http_errors.NotFoundError(message=f"Not found any user '{id_}' ID!")

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully updated protected flag of user '{id_}' ID.")

    return


@validate_call(config={"arbitrary_types_allowed": True})
async def async_get_by_email(
    async_session: AsyncSession,
    email: EmailStr,
    joins: list[str] | set[str] | None = None,
    allow_no_result: bool = False,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> UserORM | None:
    """Get user by email."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Getting user by '{email}' email...")

    _user_orm: UserORM | None = None
    try:
        _user_orm = cast(
            UserORM | None,
            await UserORM.async_get_by_where(
                async_session=async_session,
                where=[{"column": "email", "value": email}],
                joins=joins,
                allow_no_result=allow_no_result,
            ),
        )
    except NoResultFound:
        raise http_errors.NotFoundError(
            message=f"Not found any user with '{email}' email!"
        )

    if _user_orm and (warn_mode == WarnEnum.DEBUG):
        logger.debug(f"Successfully retrieved user by '{email}' email.")

    return _user_orm


@validate_call(config={"arbitrary_types_allowed": True})
async def async_get_permissions(
    async_session: AsyncSession,
    user_id: str,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> tuple[set[str], set[str]]:
    """Retrieve the roles and scopes of the user."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Retrieving roles and scopes for user '{user_id}' ID...")

    _user_orm = cast(
        UserORM,
        await UserORM.async_get(
            async_session=async_session, id=user_id, joins=["roles"]
        ),
    )
    _roles, _scopes = await _user_orm.async_get_permissions()

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(
            f"Successfully retrieved roles and scopes for user '{user_id}' ID."
        )

    return _roles, _scopes


__all__ = [
    "async_get_list",
    "async_create",
    "async_get",
    "async_update",
    "async_delete",
    "async_update_password",
    "async_update_protected",
    "async_get_by_email",
    "async_get_permissions",
]
