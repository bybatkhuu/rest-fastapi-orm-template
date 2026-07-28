from typing import cast
from collections.abc import Collection

from pydantic import validate_call
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from potato_util.constants import WarnEnum

from api.core.exceptions import http as http_errors
from api.externals.db.models.exceptions import (
    NullConstraintError,
    EmptyValueError,
    UniqueKeyError,
    RestrictViolationError,
)
from api.resources.table_stat import service as table_stat_service
from api.resources.role_scope import service as role_scope_service
from api.config import config
from api.logger import Logger, logger

from .schemas import ScopeInPM, ScopeUpPM
from .model import ScopeORM


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
) -> tuple[list[ScopeORM], int]:
    """Get list of scopes and total count."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug("Getting scope list...")

    _where = []
    if kwargs:
        for _key, _val in kwargs.items():
            _where.append({"column": _key, "op": "like", "value": _val})

    _scope_orms = cast(
        list[ScopeORM],
        await ScopeORM.async_select_by_where(
            async_session=async_session,
            where=_where,
            offset=offset,
            limit=limit,
            order_by=order_by,
            is_desc=is_desc,
            joins=joins,
        ),
    )

    _total_count = 0
    if _where:
        _total_count = await ScopeORM.async_count_by_where(
            async_session=async_session, where=_where
        )
    else:
        _total_count = await table_stat_service.async_get_row_count(
            async_session=async_session,
            table_name=ScopeORM.__tablename__,
            logger=logger,
            warn_mode=WarnEnum.DEBUG,
        )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug("Successfully retrieved scope list.")

    return _scope_orms, _total_count


@validate_call(config={"arbitrary_types_allowed": True})
async def async_create(
    async_session: AsyncSession,
    scope_in: ScopeInPM,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> ScopeORM:
    """Create a new scope."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Creating scope '{scope_in.value}' value...")

    _scope_orm: ScopeORM
    try:
        _scope_orm = cast(
            ScopeORM,
            await ScopeORM.async_insert(
                async_session=async_session, **scope_in.model_dump()
            ),
        )

        await role_scope_service.async_expand_create(
            async_session=async_session,
            scope_value=scope_in.value,
            logger=logger,
            warn_mode=WarnEnum.DEBUG,
        )

    except NullConstraintError as err:
        raise http_errors.UnprocessableEntityError(
            message="Required scope data is missing!", description=f"Scope: {err}"
        )
    except UniqueKeyError as err:
        raise http_errors.UnprocessableEntityError(
            message="Scope with the same value already exists!",
            description=f"Scope: {err}",
        )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(
            f"Successfully created scope '{scope_in.value}' value with '{_scope_orm.id}' ID."
        )

    return _scope_orm


@validate_call(config={"arbitrary_types_allowed": True})
async def async_get(
    async_session: AsyncSession,
    value: str,
    joins: Collection[str] | list[str] | set[str] | None = None,
    allow_no_result: bool = False,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> ScopeORM | None:
    """Get scope by value."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Getting scope '{value}' value...")

    _scope_orm: ScopeORM | None = None
    try:
        _scope_orm = cast(
            ScopeORM | None,
            await ScopeORM.async_get_by_where(
                async_session=async_session,
                where=[{"column": "value", "value": value}],
                joins=joins,
                allow_no_result=allow_no_result,
            ),
        )
    except NoResultFound:
        raise http_errors.NotFoundError(message=f"Not found any scope '{value}' value!")

    if _scope_orm and (warn_mode == WarnEnum.DEBUG):
        logger.debug(f"Successfully retrieved scope '{value}' value.")

    return _scope_orm


@validate_call(config={"arbitrary_types_allowed": True})
async def async_update(
    async_session: AsyncSession,
    value: str,
    scope_up: ScopeUpPM,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> ScopeORM:
    """Update scope by value."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Updating scope '{value}' value...")

    _scope_orm: ScopeORM
    try:
        _scope_orms = cast(
            list[ScopeORM],
            await ScopeORM.async_update_by_where(
                async_session=async_session,
                where=[{"column": "value", "value": value}],
                returning=True,
                allow_no_result=False,
                **scope_up.model_dump(exclude_unset=True),
            ),
        )
        _scope_orm = _scope_orms[0]
    except EmptyValueError:
        raise http_errors.UnprocessableEntityError(
            message="No scope data provided to update!"
        )
    except NoResultFound:
        raise http_errors.NotFoundError(message=f"Not found any scope '{value}' value!")
    except NullConstraintError as err:
        raise http_errors.UnprocessableEntityError(
            message="Required scope data is NULL!", description=f"Scope: {err}"
        )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully updated scope '{value}' value.")

    return _scope_orm


@validate_call(config={"arbitrary_types_allowed": True})
async def async_delete(
    async_session: AsyncSession,
    value: str,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> None:
    """Delete scope by value."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Deleting scope '{value}' value...")

    try:
        _scope_orm = cast(
            ScopeORM,
            await ScopeORM.async_get_by_where(
                async_session=async_session,
                where=[{"column": "value", "value": value}],
                allow_no_result=False,
            ),
        )

        if _scope_orm.protected:
            raise http_errors.UnprocessableEntityError(
                message=f"Scope '{value}' value is protected and cannot be deleted!"
            )

        await _scope_orm.async_delete(async_session=async_session)
    except NoResultFound:
        raise http_errors.NotFoundError(message=f"Not found any scope '{value}' value!")
    except RestrictViolationError as err:
        raise http_errors.UnprocessableEntityError(
            message=(
                "Can not delete scope because it's being used by other related data, "
                "please remove those related data first!"
            ),
            description=str(err),
        )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully deleted scope '{value}' value.")

    return


@validate_call(config={"arbitrary_types_allowed": True})
async def async_bulk_delete(
    async_session: AsyncSession,
    values: set[str],
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> None:
    """Bulk delete scopes by values."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Bulk deleting {len(values)} scope(s) by values...")

    try:
        _scope_orms: list[ScopeORM] = []
        for _value in values:
            _scope_orm = cast(
                ScopeORM,
                await ScopeORM.async_get_by_where(
                    async_session=async_session,
                    where=[{"column": "value", "value": _value}],
                ),
            )

            if not _scope_orm:
                raise http_errors.NotFoundError(
                    message=f"Not found any scope '{_value}' value!"
                )

            if _scope_orm.protected:
                raise http_errors.UnprocessableEntityError(
                    message=f"Scope '{_value}' value is protected and cannot be deleted!"
                )

            _scope_orms.append(_scope_orm)

        await ScopeORM.async_delete_objects(
            async_session=async_session, orm_objects=_scope_orms
        )
    except RestrictViolationError as err:
        raise http_errors.UnprocessableEntityError(
            message=(
                "Can not delete scope(s) because they are being used by other related data, "
                "please remove those related data first!"
            ),
            description=str(err),
        )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully deleted {len(values)} scope(s) by values.")

    return


@validate_call(config={"arbitrary_types_allowed": True})
async def async_update_protected(
    async_session: AsyncSession,
    value: str,
    protected: bool,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> None:
    """Update protected flag of scope by value."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Updating protected flag of scope '{value}' value...")

    try:
        await ScopeORM.async_update_by_where(
            async_session=async_session,
            where=[{"column": "value", "value": value}],
            allow_no_result=False,
            protected=protected,
        )
    except NoResultFound:
        raise http_errors.NotFoundError(message=f"Not found any scope '{value}' value!")

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully updated protected flag of scope '{value}' value.")

    return


@validate_call(config={"arbitrary_types_allowed": True})
async def async_bulk_update_protected(
    async_session: AsyncSession,
    values: set[str],
    protected: bool,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> None:
    """Bulk update protected flag of scopes by values."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(
            f"Bulk updating protected flag of {len(values)} scope(s) by values..."
        )

    _value: str | None = None
    try:
        for _value in values:
            await ScopeORM.async_update_by_where(
                async_session=async_session,
                where=[{"column": "value", "value": _value}],
                allow_no_result=False,
                protected=protected,
            )
    except NoResultFound:
        raise http_errors.NotFoundError(
            message=f"Not found any scope '{_value}' value!"
        )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(
            f"Successfully updated protected flag of {len(values)} scope(s) by values."
        )

    return


__all__ = [
    "async_get_list",
    "async_create",
    "async_get",
    "async_update",
    "async_delete",
    "async_update_protected",
    "async_bulk_delete",
    "async_bulk_update_protected",
]
