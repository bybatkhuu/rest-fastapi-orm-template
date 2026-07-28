from typing import cast, Any
from datetime import datetime
from collections.abc import Collection

from pydantic import validate_call, SecretStr
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from potato_util.constants import WarnEnum
from potato_util.dt import calc_future_dt, now_utc_dt
from potato_util.crypto import hash as hash_utils
from potato_util.generator import gen_random_string

from api.core.exceptions import http as http_errors
from api.externals.db.models.exceptions import (
    NullConstraintError,
    EmptyValueError,
    UniqueKeyError,
    ForeignKeyError,
)
from api.resources.table_stat import service as table_stat_service
from api.config import config
from api.logger import Logger, logger

from .schemas import (
    UserTokenInPM,
    UserTokenUpPM,
    UserTokenKindEnum,
    UserTokenStatusEnum,
)
from .model import UserTokenORM


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
) -> tuple[list[UserTokenORM], int]:
    """Get list of user tokens and total count."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug("Getting user token list...")

    _where = []
    if kwargs:
        for _key, _val in kwargs.items():
            _where.append({"column": _key, "value": _val})

    _user_token_orms = cast(
        list[UserTokenORM],
        await UserTokenORM.async_select_by_where(
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
        _total_count = await UserTokenORM.async_count_by_where(
            async_session=async_session, where=_where
        )
    else:
        _total_count = await table_stat_service.async_get_row_count(
            async_session=async_session,
            table_name=UserTokenORM.__tablename__,
            logger=logger,
            warn_mode=WarnEnum.DEBUG,
        )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug("Successfully retrieved user token list.")

    return _user_token_orms, _total_count


@validate_call(config={"arbitrary_types_allowed": True})
async def async_create(
    async_session: AsyncSession,
    user_token_in: UserTokenInPM,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> UserTokenORM:
    """Create a new user token."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(
            f"Creating '{user_token_in.kind}' token for user '{user_token_in.user_id}' ID..."
        )

    _user_token_orm: UserTokenORM
    try:
        _user_token_dict = user_token_in.model_dump(exclude={"token"})
        _user_token_dict["token_hash"] = hash_utils.hash(
            val=user_token_in.token.get_secret_value(),
            algorithm=config.api.security.token.hash_algorithm,
        )
        _user_token_orm = cast(
            UserTokenORM,
            await UserTokenORM.async_insert(
                async_session=async_session, **_user_token_dict
            ),
        )
    except NullConstraintError as err:
        raise http_errors.UnprocessableEntityError(
            message="Required user token data is missing!",
            description=f"UserToken: {err}",
        )
    except UniqueKeyError as err:
        raise http_errors.UnprocessableEntityError(
            message="User token with the same user ID, kind and token hash already exists!",
            description=f"UserToken: {err}",
        )
    except ForeignKeyError as err:
        raise http_errors.UnprocessableEntityError(
            message="Related user ID does not exist!", description=f"UserToken: {err}"
        )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(
            f"Successfully created '{user_token_in.kind}' token for user '{user_token_in.user_id}' ID and token "
            f"'{_user_token_orm.id}' ID."
        )

    return _user_token_orm


@validate_call(config={"arbitrary_types_allowed": True})
async def async_get(
    async_session: AsyncSession,
    id_: str,
    joins: Collection[str] | list[str] | set[str] | None = None,
    allow_no_result: bool = False,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> UserTokenORM | None:
    """Get user token by ID."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Getting user token '{id_}' ID...")

    _user_token_orm: UserTokenORM | None = None
    try:
        _user_token_orm = cast(
            UserTokenORM | None,
            await UserTokenORM.async_get(
                async_session=async_session,
                id=id_,
                joins=joins,
                allow_no_result=allow_no_result,
            ),
        )
    except NoResultFound:
        raise http_errors.NotFoundError(message=f"Not found any user token '{id_}' ID!")

    if _user_token_orm and (warn_mode == WarnEnum.DEBUG):
        logger.debug(f"Successfully retrieved user token '{id_}' ID.")

    return _user_token_orm


@validate_call(config={"arbitrary_types_allowed": True})
async def async_update(
    async_session: AsyncSession,
    id_: str,
    user_token_up: UserTokenUpPM,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> UserTokenORM:
    """Update user token by ID."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Updating user token '{id_}' ID...")

    _user_token_orm: UserTokenORM
    try:
        _user_token_orm = cast(
            UserTokenORM,
            await UserTokenORM.async_update_by_id(
                async_session=async_session,
                id=id_,
                **user_token_up.model_dump(exclude_unset=True),
            ),
        )
    except EmptyValueError:
        raise http_errors.UnprocessableEntityError(
            message="No user token data provided to update!"
        )
    except NoResultFound:
        raise http_errors.NotFoundError(message=f"Not found any user token '{id_}' ID!")
    except NullConstraintError as err:
        raise http_errors.UnprocessableEntityError(
            message="Required user token data is NULL!", description=f"UserToken: {err}"
        )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully updated user token '{id_}' ID.")

    return _user_token_orm


@validate_call(config={"arbitrary_types_allowed": True})
async def async_delete(
    async_session: AsyncSession,
    id_: str,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> None:
    """Delete user token by ID."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Deleting user token '{id_}' ID...")

    try:
        await UserTokenORM.async_delete_by_id(async_session=async_session, id=id_)
    except NoResultFound:
        raise http_errors.NotFoundError(message=f"Not found any user token '{id_}' ID!")

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully deleted user token '{id_}' ID.")

    return


@validate_call(config={"arbitrary_types_allowed": True})
async def async_generate(
    async_session: AsyncSession,
    user_id: str,
    kind: UserTokenKindEnum,
    expires_at: datetime | None = None,
    family_token_id: str | None = None,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> tuple[SecretStr, UserTokenORM]:
    """Generate a new user token."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Generating '{kind}' token for user '{user_id}' ID...")

    if not expires_at:
        _duration = 0
        if kind == UserTokenKindEnum.REFRESH:
            _duration = config.api.security.token.refresh_duration
        elif kind == UserTokenKindEnum.RESET:
            _duration = config.api.security.token.reset_duration

        expires_at = calc_future_dt(delta=_duration)

    _token = SecretStr(gen_random_string(length=config.api.security.token.length))
    _user_token_dict = {
        "kind": kind,
        "token": _token,
        "expires_at": expires_at,
        "family_token_id": family_token_id,
        "user_id": user_id,
    }

    _user_token_orm = await async_create(
        async_session=async_session,
        user_token_in=_user_token_dict,  # type: ignore
        logger=logger,
        warn_mode=WarnEnum.DEBUG,
    )

    if (kind == UserTokenKindEnum.REFRESH) and (not family_token_id):
        _user_token_orm.family_token_id = _user_token_orm.id

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully generated '{kind}' token for user '{user_id}' ID.")

    return _token, _user_token_orm


@validate_call(config={"arbitrary_types_allowed": True})
async def async_get_by_token(
    async_session: AsyncSession,
    token: SecretStr,
    user_id: str | None = None,
    kind: UserTokenKindEnum | None = None,
    status: UserTokenStatusEnum | None = None,
    joins: Collection[str] | list[str] | set[str] | None = None,
    allow_no_result: bool = True,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> UserTokenORM | None:
    """Get user token by token."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Getting '{kind}' token with user '{user_id}' ID...")

    _user_token_orm: UserTokenORM | None = None
    try:
        _where: list[dict[str, Any]] = []
        if user_id:
            _where.append({"column": "user_id", "value": user_id})

        if kind:
            _where.append({"column": "kind", "value": kind})

        _token_hash = hash_utils.hash(
            val=token.get_secret_value(),
            algorithm=config.api.security.token.hash_algorithm,
        )
        _where.append({"column": "token_hash", "value": _token_hash})

        if status:
            _where.append({"column": "status", "value": status})

        _user_token_orm = cast(
            UserTokenORM | None,
            await UserTokenORM.async_get_by_where(
                async_session=async_session,
                where=_where,
                joins=joins,
                allow_no_result=allow_no_result,
            ),
        )
    except NoResultFound:
        raise http_errors.NotFoundError(message="Not found any user token!")

    if _user_token_orm and (warn_mode == WarnEnum.DEBUG):
        logger.debug(f"Successfully retrieved '{kind}' token with user '{user_id}' ID.")

    return _user_token_orm


@validate_call(config={"arbitrary_types_allowed": True})
async def async_block_refresh_tokens(
    async_session: AsyncSession,
    family_token_id: str,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> None:
    """Block user refresh tokens by family token ID."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(
            f"Blocking user refresh tokens by family token '{family_token_id}' ID..."
        )

    await UserTokenORM.async_update_by_where(
        async_session=async_session,
        where=[{"column": "family_token_id", "value": family_token_id}],
        status=UserTokenStatusEnum.BLOCKED,
    )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(
            f"Successfully blocked user refresh tokens by family token '{family_token_id}' ID."
        )

    return


@validate_call(config={"arbitrary_types_allowed": True})
async def async_revoke_refresh_tokens(
    async_session: AsyncSession,
    user_id: str,
    skip_refresh_token: SecretStr | None = None,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> None:
    """Revoke all active refresh tokens of the user."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Revoking all active refresh tokens of user '{user_id}' ID...")

    _where: list[dict[str, Any]] = [
        {"column": "user_id", "value": user_id},
        {"column": "kind", "value": UserTokenKindEnum.REFRESH},
        {"column": "status", "value": UserTokenStatusEnum.ACTIVE},
    ]

    if skip_refresh_token:
        _token_hash = hash_utils.hash(
            val=skip_refresh_token.get_secret_value(),
            algorithm=config.api.security.token.hash_algorithm,
        )
        _where.append({"column": "token_hash", "op": "!=", "value": _token_hash})

    _user_token_orms = await UserTokenORM.async_update_by_where(
        async_session=async_session,
        where=_where,
        status=UserTokenStatusEnum.REVOKED,
        revoked_at=now_utc_dt(),
        returning=True,
    )
    _affected_count = len(_user_token_orms)

    logger.success(
        f"Successfully revoked active refresh tokens of user '{user_id}' ID: {_affected_count}."
    )
    return


__all__ = [
    "async_get_list",
    "async_create",
    "async_get",
    "async_update",
    "async_delete",
    "async_generate",
    "async_get_by_token",
    "async_block_refresh_tokens",
    "async_revoke_refresh_tokens",
]
