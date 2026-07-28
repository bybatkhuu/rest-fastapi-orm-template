from typing import cast

from pydantic import validate_call
from sqlalchemy.ext.asyncio import AsyncSession

from potato_util.constants import WarnEnum

from api.logger import Logger, logger

from .model import TableStatORM


@validate_call(config={"arbitrary_types_allowed": True})
async def async_get_row_count(
    async_session: AsyncSession,
    table_name: str,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> int:
    """Get count of rows from the table stat by table name."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Getting row count of '{table_name}' table from table stat...")

    _table_stat_orm = cast(
        TableStatORM | None,
        await TableStatORM.async_get_by_where(
            async_session=async_session,
            where={"column": "table_name", "value": table_name},
        ),
    )

    _row_scount = 0
    if _table_stat_orm:
        _row_scount = _table_stat_orm.row_count

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(
            f"Successfully got row count of '{table_name}' table: {_row_scount}."
        )

    return _row_scount


__all__ = [
    "async_get_row_count",
]
