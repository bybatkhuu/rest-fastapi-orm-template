from typing import cast

from pydantic import validate_call
from sqlalchemy.ext.asyncio import AsyncSession

from potato_util.constants import WarnEnum

from api.logger import async_log_mode

from .model import TableStatORM


@validate_call(config={"arbitrary_types_allowed": True})
async def async_get_row_count(
    async_session: AsyncSession,
    request_id: str,
    table_name: str,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> int:
    """Get count of rows from the table stat by table name.

    Args:
        async_session (AsyncSession, required): SQLAlchemy async_session for database connection.
        request_id    (str         , required): ID of the request.
        table_name    (str         , required): Name of the table.
        warn_mode     (WarnEnum    , optional): Warning mode. Defaults to `WarnEnum.IGNORE`.

    Returns:
        int: Count of rows.
    """

    await async_log_mode(
        message=f"[{request_id}] - Getting row count of '{table_name}' table from table stat...",
        warn_mode=warn_mode,
    )

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

    await async_log_mode(
        message=f"[{request_id}] - Successfully got row count of '{table_name}' table: {_row_scount}.",
        level="SUCCESS",
        warn_mode=warn_mode,
    )
    return _row_scount


__all__ = [
    "async_get_row_count",
]
