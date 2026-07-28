from typing import cast, Any
from collections.abc import Collection

from pydantic import validate_call, SecretStr
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from potato_util.constants import WarnEnum
from potato_util.crypto import hash as hash_utils
from potato_util.dt import now_utc_dt

from api.core.exceptions import http as http_errors
from api.externals.db.models.exceptions import (
    NullConstraintError,
    EmptyValueError,
    UniqueKeyError,
    ForeignKeyError,
)
from api.resources.table_stat import service as table_stat_service
from api.resources.scope import service as scope_service
from api.config import config
from api.logger import Logger, logger

from .schemas import ApiKeyInPM, ApiKeyUpPM, ApiKeyStatusEnum
from .model import UserApiKeyORM
from .utils import generate_api_key


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
) -> tuple[list[UserApiKeyORM], int]:
    """Get list of API keys and total count."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug("Getting API key list...")

    _where = []
    if kwargs:
        for _key, _val in kwargs.items():
            if _key == "key_prefix":
                _where.append({"column": _key, "op": "like", "value": _val})
            else:
                _where.append({"column": _key, "value": _val})

    _api_key_orms = cast(
        list[UserApiKeyORM],
        await UserApiKeyORM.async_select_by_where(
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
        _total_count = await UserApiKeyORM.async_count_by_where(
            async_session=async_session, where=_where
        )
    else:
        _total_count = await table_stat_service.async_get_row_count(
            async_session=async_session,
            table_name=UserApiKeyORM.__tablename__,
            logger=logger,
            warn_mode=WarnEnum.DEBUG,
        )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug("Successfully retrieved API key list.")

    return _api_key_orms, _total_count


@validate_call(config={"arbitrary_types_allowed": True})
async def async_create(
    async_session: AsyncSession,
    user_id: str,
    api_key_in: ApiKeyInPM,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> tuple[SecretStr, UserApiKeyORM]:
    """Create a new API key."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Creating API key for user '{user_id}' ID...")

    _full_api_key: SecretStr
    _api_key_orm: UserApiKeyORM
    try:
        _allowed_scopes = api_key_in.allowed_scopes
        if _allowed_scopes:
            for _scope in _allowed_scopes:
                _scope_orm = await scope_service.async_get(
                    async_session=async_session,
                    value=_scope,
                    allow_no_result=True,
                    logger=logger,
                    warn_mode=WarnEnum.DEBUG,
                )

                if not _scope_orm:
                    raise http_errors.UnprocessableEntityError(
                        message=f"Scope '{_scope}' does not exist!"
                    )

        _api_key_dict = api_key_in.model_dump()
        _key_prefix, _raw_api_key, _full_api_key = generate_api_key()

        _api_key_dict["key_prefix"] = _key_prefix
        _api_key_dict["key_hash"] = hash_utils.hash(
            val=_raw_api_key.get_secret_value(),
            algorithm=config.api.security.api_key.hash_algorithm,
        )
        _api_key_dict["status"] = ApiKeyStatusEnum.ACTIVE
        _api_key_dict["user_id"] = user_id

        _api_key_orm = cast(
            UserApiKeyORM,
            await UserApiKeyORM.async_insert(
                async_session=async_session, **_api_key_dict
            ),
        )
    except NullConstraintError as err:
        raise http_errors.UnprocessableEntityError(
            message="Required API key data is missing!",
            description=f"UserApiKey: {err}",
        )
    except UniqueKeyError as err:
        raise http_errors.UnprocessableEntityError(
            message="API key with the same key prefix and key hash already exists!",
            description=f"UserApiKey: {err}",
        )
    except ForeignKeyError as err:
        raise http_errors.UnprocessableEntityError(
            message="Related user ID does not exist!", description=f"UserApiKey: {err}"
        )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(
            f"Successfully created API key '{_api_key_orm.id}' ID for user '{user_id}' ID."
        )

    return _full_api_key, _api_key_orm


@validate_call(config={"arbitrary_types_allowed": True})
async def async_get(
    async_session: AsyncSession,
    id_: str,
    user_id: str | None = None,
    joins: Collection[str] | list[str] | set[str] | None = None,
    allow_no_result: bool = False,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> UserApiKeyORM | None:
    """Get API key by ID and optionally by user ID."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Getting API key '{id_}' ID...")

    _api_key_orm: UserApiKeyORM | None = None
    try:
        _where: list[dict[str, Any]] = [{"column": "id", "value": id_}]
        if user_id:
            _where.append({"column": "user_id", "value": user_id})

        _api_key_orm = cast(
            UserApiKeyORM | None,
            await UserApiKeyORM.async_get_by_where(
                async_session=async_session,
                where=_where,
                joins=joins,
                allow_no_result=allow_no_result,
            ),
        )
    except NoResultFound:
        raise http_errors.NotFoundError(message=f"Not found any API key '{id_}' ID!")

    if _api_key_orm and (warn_mode == WarnEnum.DEBUG):
        logger.debug(f"Successfully retrieved API key '{id_}' ID.")

    return _api_key_orm


@validate_call(config={"arbitrary_types_allowed": True})
async def async_update(
    async_session: AsyncSession,
    id_: str,
    api_key_up: ApiKeyUpPM,
    user_id: str | None = None,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> UserApiKeyORM:
    """Update API key by ID."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Updating API key '{id_}' ID...")

    _api_key_orm: UserApiKeyORM
    try:
        _allowed_scopes = api_key_up.allowed_scopes
        if _allowed_scopes:
            for _scope in _allowed_scopes:
                _scope_orm = await scope_service.async_get(
                    async_session=async_session,
                    value=_scope,
                    allow_no_result=True,
                    logger=logger,
                    warn_mode=WarnEnum.DEBUG,
                )

                if not _scope_orm:
                    raise http_errors.UnprocessableEntityError(
                        message=f"Scope '{_scope}' does not exist!"
                    )

        _where: list[dict[str, Any]] = [{"column": "id", "value": id_}]
        if user_id:
            _where.append({"column": "user_id", "value": user_id})

        _api_key_orms = cast(
            list[UserApiKeyORM],
            await UserApiKeyORM.async_update_by_where(
                async_session=async_session,
                where=_where,
                returning=True,
                allow_no_result=False,
                **api_key_up.model_dump(exclude_unset=True),
            ),
        )
        _api_key_orm = _api_key_orms[0]
    except EmptyValueError:
        raise http_errors.UnprocessableEntityError(
            message="No API key data provided to update!"
        )
    except NoResultFound:
        raise http_errors.NotFoundError(message=f"Not found any API key '{id_}' ID!")
    except NullConstraintError as err:
        raise http_errors.UnprocessableEntityError(
            message="Required API key data is NULL!", description=f"UserApiKey: {err}"
        )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully updated API key '{id_}' ID.")

    return _api_key_orm


@validate_call(config={"arbitrary_types_allowed": True})
async def async_delete(
    async_session: AsyncSession,
    id_: str,
    user_id: str | None = None,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> None:
    """Delete API key by ID."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Deleting API key '{id_}' ID...")

    try:
        _where: list[dict[str, Any]] = [{"column": "id", "value": id_}]
        if user_id:
            _where.append({"column": "user_id", "value": user_id})

        await UserApiKeyORM.async_delete_by_where(
            async_session=async_session, where=_where
        )
    except NoResultFound:
        raise http_errors.NotFoundError(message=f"Not found any API key '{id_}' ID!")

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully deleted API key '{id_}' ID.")

    return


@validate_call(config={"arbitrary_types_allowed": True})
async def async_get_by_api_key(
    async_session: AsyncSession,
    api_key: SecretStr,
    status: ApiKeyStatusEnum | None = None,
    joins: list[str] | set[str] | None = None,
    allow_no_result: bool = True,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> UserApiKeyORM | None:
    """Get API key by the raw key value."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug("Getting API key...")

    _api_key_orm: UserApiKeyORM | None = None
    try:
        _where: list[dict[str, Any]] = []
        _api_key_value = api_key.get_secret_value()
        _api_key_parts = _api_key_value.split(config.api.security.api_key.separator)
        _key_prefix = _api_key_parts[0]
        _raw_api_key = _api_key_parts[1]

        _key_hash = hash_utils.hash(
            val=_raw_api_key, algorithm=config.api.security.api_key.hash_algorithm
        )
        _where.append({"column": "key_prefix", "value": _key_prefix})
        _where.append({"column": "key_hash", "value": _key_hash})

        if status:
            _where.append({"column": "status", "value": status})

        _api_key_orm = cast(
            UserApiKeyORM | None,
            await UserApiKeyORM.async_get_by_where(
                async_session=async_session,
                where=_where,
                joins=joins,
                allow_no_result=allow_no_result,
            ),
        )
    except NoResultFound:
        raise http_errors.NotFoundError(message="Not found any API key!")

    if _api_key_orm and (warn_mode == WarnEnum.DEBUG):
        logger.debug("Successfully retrieved API key.")

    return _api_key_orm


@validate_call(config={"arbitrary_types_allowed": True})
async def async_update_status(
    async_session: AsyncSession,
    id_: str,
    status: ApiKeyStatusEnum,
    user_id: str | None = None,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> None:
    """Update API key status by ID."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Updating status of API key '{id_}' ID...")

    try:
        _where: list[dict[str, Any]] = [{"column": "id", "value": id_}]
        if user_id:
            _where.append({"column": "user_id", "value": user_id})

        await UserApiKeyORM.async_update_by_where(
            async_session=async_session,
            where=_where,
            allow_no_result=False,
            status=status,
        )
    except NoResultFound:
        raise http_errors.NotFoundError(message=f"Not found any API key '{id_}' ID!")

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully updated status of API key '{id_}' ID.")

    return


@validate_call(config={"arbitrary_types_allowed": True})
async def async_revoke(
    async_session: AsyncSession,
    id_: str,
    user_id: str | None = None,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> None:
    """Revoke API key by ID."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Revoking API key '{id_}' ID...")

    try:
        _where: list[dict[str, Any]] = [{"column": "id", "value": id_}]
        if user_id:
            _where.append({"column": "user_id", "value": user_id})

        await UserApiKeyORM.async_update_by_where(
            async_session=async_session,
            where=_where,
            status=ApiKeyStatusEnum.REVOKED,
            revoked_at=now_utc_dt(),
            allow_no_result=False,
        )
    except NoResultFound:
        raise http_errors.NotFoundError(message=f"Not found any API key '{id_}' ID!")

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully revoked API key '{id_}' ID.")

    return


__all__ = [
    "async_get_list",
    "async_create",
    "async_get",
    "async_update",
    "async_delete",
    "async_get_by_api_key",
    "async_update_status",
    "async_revoke",
]
