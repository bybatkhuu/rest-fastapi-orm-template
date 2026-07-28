from typing import cast

from pydantic import validate_call
from sqlalchemy.ext.asyncio import AsyncSession

from potato_util.constants import WarnEnum

from api.core.exceptions import http as http_errors
from api.externals.db.models.exceptions import UniqueKeyError
from api.logger import Logger, logger

from .model import RoleScopeORM


@validate_call(config={"arbitrary_types_allowed": True})
async def async_expand_create(
    async_session: AsyncSession,
    scope_value: str,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> None:
    """Check role_scope records to expand new scope value for `all`, `*`, `prefix:all` or `prefix:*` role_scope
    records.
    """

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(
            f"Checking role_scope records to expand new scope '{scope_value}' value for `all`, `*`, `prefix:all` "
            "or `prefix:*` role_scope records..."
        )

    try:
        _role_scope_orms = cast(
            list[RoleScopeORM],
            await RoleScopeORM.async_select(async_session=async_session, limit=0),
        )
        for _role_scope_orm in _role_scope_orms:
            # ! Browser cookie limit is 4KB, so disabled to expand all scopes temporarily.
            # if (_role_scope_orm.scope_value == "all") or (
            #     _role_scope_orm.scope_value == "*"
            # ):
            #     await RoleScopeORM.async_insert(
            #         async_session=async_session,
            #         role_name=_role_scope_orm.role_name,
            #         scope_value=scope_value,
            #         returning=False,
            #     )

            if _role_scope_orm.scope_value.endswith(":all"):
                _prefix = _role_scope_orm.scope_value.removesuffix(":all")
                if scope_value.startswith(_prefix):
                    await RoleScopeORM.async_insert(
                        async_session=async_session,
                        role_name=_role_scope_orm.role_name,
                        scope_value=scope_value,
                        returning=False,
                    )
            elif _role_scope_orm.scope_value.endswith(":*"):
                _prefix = _role_scope_orm.scope_value.removesuffix(":*")
                if scope_value.startswith(_prefix):
                    await RoleScopeORM.async_insert(
                        async_session=async_session,
                        role_name=_role_scope_orm.role_name,
                        scope_value=scope_value,
                        returning=False,
                    )

    except UniqueKeyError as err:
        raise http_errors.UnprocessableEntityError(
            message="Role scope record already exists for the new scope value.",
            description=f"RoleScope: {err}",
        )

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(
            "Successfully checked role_scope records to expand new scope value."
        )

    return


__all__ = [
    "async_expand_create",
]
