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
    NotFoundError,
)
from api.resources.scope.model import ScopeORM
from api.resources.scope import service as scope_service
from api.resources.role_scope import utils as role_scope_utils
from api.resources.table_stat import service as table_stat_service
from api.config import config
from api.logger import Logger, logger

from .schemas import RoleInPM, RoleUpPM
from .model import RoleORM


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
) -> tuple[list[RoleORM], int]:
    """Get list of roles and total count."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug("Getting role list...")

    _where = []
    if kwargs:
        for _key, _val in kwargs.items():
            _where.append({"column": _key, "op": "like", "value": _val})

    _role_orms = cast(
        list[RoleORM],
        await RoleORM.async_select_by_where(
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
        _total_count = await RoleORM.async_count_by_where(
            async_session=async_session, where=_where
        )
    else:
        _total_count = await table_stat_service.async_get_row_count(
            async_session=async_session,
            table_name=RoleORM.__tablename__,
            logger=logger,
            warn_mode=WarnEnum.DEBUG,
        )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug("Successfully retrieved role list.")

    return _role_orms, _total_count


@validate_call(config={"arbitrary_types_allowed": True})
async def async_create(
    async_session: AsyncSession,
    role_in: RoleInPM,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> RoleORM:
    """Create a new role."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Creating role '{role_in.name}' name...")

    _role_orm: RoleORM
    try:
        _all_scope_orms, _ = await scope_service.async_get_list(
            async_session=async_session,
            limit=0,
            logger=logger,
            warn_mode=WarnEnum.DEBUG,
        )
        _scope_orms = role_scope_utils.expand_scopes(
            target_scopes=role_in.scopes, pool_scope_orms=_all_scope_orms
        )

        _role_orm = cast(
            RoleORM,
            await RoleORM.async_insert(
                async_session=async_session, **role_in.model_dump(exclude={"scopes"})
            ),
        )

        await _role_orm.awaitable_attrs.scopes
        if _scope_orms:
            _role_orm.scopes = _scope_orms

    except NotFoundError as err:
        raise http_errors.UnprocessableEntityError(
            message="Not found some scope(s)!", description=f"Role: {err}"
        )
    except NullConstraintError as err:
        raise http_errors.UnprocessableEntityError(
            message="Required role data is missing!", description=f"Role: {err}"
        )
    except UniqueKeyError as err:
        raise http_errors.UnprocessableEntityError(
            message="Role with the same name already exists!",
            description=f"Role: {err}",
        )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(
            f"Successfully created role '{role_in.name}' name with '{_role_orm.id}' ID."
        )

    return _role_orm


@validate_call(config={"arbitrary_types_allowed": True})
async def async_get(
    async_session: AsyncSession,
    name: str,
    joins: Collection[str] | list[str] | set[str] | None = None,
    allow_no_result: bool = False,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> RoleORM | None:
    """Get role by name."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Getting role '{name}' name...")

    _role_orm: RoleORM | None = None
    try:
        _role_orm = cast(
            RoleORM | None,
            await RoleORM.async_get_by_where(
                async_session=async_session,
                where=[{"column": "name", "value": name}],
                joins=joins,
                allow_no_result=allow_no_result,
            ),
        )
    except NoResultFound:
        raise http_errors.NotFoundError(message=f"Not found any role '{name}' name!")

    if _role_orm and (warn_mode == WarnEnum.DEBUG):
        logger.debug(f"Successfully retrieved role '{name}' name.")

    return _role_orm


@validate_call(config={"arbitrary_types_allowed": True})
async def async_update(
    async_session: AsyncSession,
    name: str,
    role_up: RoleUpPM,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> RoleORM:
    """Update role by name."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Updating role '{name}' name...")

    _role_orm: RoleORM
    try:
        _role_orm = cast(
            RoleORM,
            await async_get(
                async_session=async_session,
                name=name,
                logger=logger,
                warn_mode=WarnEnum.DEBUG,
            ),
        )

        _role_up_dict = role_up.model_dump(exclude_unset=True)
        if "scopes" in _role_up_dict:
            _scopes_up = _role_up_dict.pop("scopes", set[str]())

            if _role_orm.protected and _scopes_up:
                raise http_errors.UnprocessableEntityError(
                    message=f"Role '{name}' name is protected and cannot update scopes!"
                )

            _all_scope_orms, _ = await scope_service.async_get_list(
                async_session=async_session,
                limit=0,
                logger=logger,
                warn_mode=WarnEnum.DEBUG,
            )
            _scope_orms = role_scope_utils.expand_scopes(
                target_scopes=_scopes_up, pool_scope_orms=_all_scope_orms
            )

            await _role_orm.awaitable_attrs.scopes
            if _scope_orms:
                _role_up_dict["scopes"] = _scope_orms

        await _role_orm.async_update(async_session=async_session, **_role_up_dict)
    except NotFoundError as err:
        raise http_errors.UnprocessableEntityError(
            message="Not found some scope(s)!", description=f"Role: {err}"
        )
    except EmptyValueError:
        raise http_errors.UnprocessableEntityError(
            message="No role data provided to update!"
        )
    except NoResultFound:
        raise http_errors.NotFoundError(message=f"Not found any role '{name}' name!")
    except NullConstraintError as err:
        raise http_errors.UnprocessableEntityError(
            message="Required role data is NULL!", description=f"Role: {err}"
        )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully updated role '{name}' name.")

    return _role_orm


@validate_call(config={"arbitrary_types_allowed": True})
async def async_delete(
    async_session: AsyncSession,
    name: str,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> None:
    """Delete role by name."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Deleting role '{name}' name...")

    try:
        _role_orm = cast(
            RoleORM,
            await RoleORM.async_get_by_where(
                async_session=async_session,
                where=[{"column": "name", "value": name}],
                allow_no_result=False,
            ),
        )

        if _role_orm.protected:
            raise http_errors.UnprocessableEntityError(
                message=f"Role '{name}' name is protected and cannot be deleted!"
            )

        await _role_orm.async_delete(async_session=async_session)
    except NoResultFound:
        raise http_errors.NotFoundError(message=f"Not found any role '{name}' name!")
    except RestrictViolationError as err:
        raise http_errors.UnprocessableEntityError(
            message=(
                "Can not delete role because it's being used by other related resource data, "
                "please remove those related resource data first!"
            ),
            description=str(err),
        )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully deleted role '{name}' name.")

    return


@validate_call(config={"arbitrary_types_allowed": True})
async def async_update_protected(
    async_session: AsyncSession,
    name: str,
    protected: bool,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> None:
    """Update protected flag of role by name."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Updating protected flag of role '{name}' name...")

    try:
        await RoleORM.async_update_by_where(
            async_session=async_session,
            where=[{"column": "name", "value": name}],
            allow_no_result=False,
            protected=protected,
        )
    except NoResultFound:
        raise http_errors.NotFoundError(message=f"Not found any role '{name}' name!")

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully updated protected flag of role '{name}' name.")

    return


@validate_call(config={"arbitrary_types_allowed": True})
async def async_get_scopes(
    async_session: AsyncSession,
    name: str,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> list[ScopeORM]:
    """Get scopes of role by name."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Getting scopes of role '{name}' name...")

    try:
        _role_orm = cast(
            RoleORM,
            await RoleORM.async_get_by_where(
                async_session=async_session,
                where=[{"column": "name", "value": name}],
                joins=["scopes"],
                allow_no_result=False,
            ),
        )

        _scope_orms: list[ScopeORM] = []
        await _role_orm.awaitable_attrs.scopes
        if _role_orm.scopes:
            _scope_orms = _role_orm.scopes

    except NoResultFound:
        raise http_errors.NotFoundError(message=f"Not found any role '{name}' name!")

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully retrieved scopes of role '{name}' name.")

    return _scope_orms


__all__ = [
    "async_get_list",
    "async_create",
    "async_get",
    "async_update",
    "async_delete",
    "async_update_protected",
    "async_get_scopes",
]
