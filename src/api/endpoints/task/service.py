from pydantic import validate_call
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from potato_util.constants import WarnEnum

from api.core.constants import ErrorCodeEnum
from api.config import config
from api.core.exceptions import BaseHTTPException, EmptyValueError, NullConstraintError
from api.endpoints.table_stat import service as table_stat_service
from api.logger import async_log_mode

from .schemas import TaskBasePM
from .model import TaskORM


@validate_call(config={"arbitrary_types_allowed": True})
async def async_get_list(
    async_session: AsyncSession,
    request_id: str,
    offset: int = 0,
    limit: int = config.db.select_limit,
    is_desc: bool = config.db.select_is_desc,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
    **kwargs,
) -> tuple[list[TaskORM], int]:
    """Get list of tasks and total count.

    Args:
        async_session (AsyncSession, required): SQLAlchemy async_session for database connection.
        request_id    (str         , required): ID of the request.
        offset        (int         , optional): Offset of the query. Defaults to 0.
        limit         (int         , optional): Limit of the query. Defaults to `config.db.select_limit`.
        is_desc       (bool        , optional): Is descending or ascending. Defaults to `config.db.select_is_desc`.
        warn_mode     (WarnEnum    , optional): Warning mode. Defaults to `WarnEnum.IGNORE`.
        **kwargs      (dict        , optional): Column and value as key-value pair for filtering.

    Returns:
        Tuple[List[TaskORM], int]: List of tasks and total count as tuple.
    """

    await async_log_mode(
        message=f"[{request_id}] - Getting task list...", warn_mode=warn_mode
    )

    _where = []
    if kwargs:
        for _key, _val in kwargs.items():
            _where.append({"column": _key, "value": _val})

    _orm_tasks: list[TaskORM] = await TaskORM.async_select_by_where(
        async_session=async_session,
        where=_where,
        offset=offset,
        limit=limit,
        is_desc=is_desc,
    )

    _all_count = 0
    if _where:
        _all_count = await TaskORM.async_count_by_where(
            async_session=async_session, where=_where
        )
    else:
        _all_count = await table_stat_service.async_get_row_count(
            async_session=async_session,
            request_id=request_id,
            table_name=TaskORM.__tablename__,
            warn_mode=WarnEnum.DEBUG,
        )

    await async_log_mode(
        message=f"[{request_id}] - Successfully retrieved task list.",
        level="SUCCESS",
        warn_mode=warn_mode,
    )
    return _orm_tasks, _all_count


@validate_call(config={"arbitrary_types_allowed": True})
async def async_create(
    async_session: AsyncSession,
    request_id: str,
    task_in: TaskBasePM,
    auto_commit: bool = False,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> TaskORM:
    """Create a new task.

    Args:
        async_session (AsyncSession, required): SQLAlchemy async_session for database connection.
        request_id    (str         , required): ID of the request.
        task_in       (TaskBasePM  , required): New task data to create.
        auto_commit   (bool        , optional): Auto commit. Defaults to False.
        warn_mode     (WarnEnum    , optional): Warning mode. Defaults to `WarnEnum.IGNORE`.

    Raises:
        BaseHTTPException: If task data is missing.

    Returns:
        TaskORM: New TaskORM model.
    """

    await async_log_mode(
        message=f"[{request_id}] - Creating task...", warn_mode=warn_mode
    )

    _task_orm: TaskORM
    try:
        _task_orm: TaskORM = await TaskORM.async_insert(
            async_session=async_session,
            auto_commit=auto_commit,
            **task_in.model_dump(),
        )

        await async_log_mode(
            message=f"[{request_id}] - Successfully created task with '{_task_orm.id}' ID.",
            level="SUCCESS",
            warn_mode=warn_mode,
        )
    except NullConstraintError as err:
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.UNPROCESSABLE_ENTITY,
            message="Task data is missing!",
            description=f"Task: {err}",
        )

    return _task_orm


@validate_call(config={"arbitrary_types_allowed": True})
async def async_get(
    async_session: AsyncSession,
    request_id: str,
    id: str,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> TaskORM:
    """Get task by ID.

    Args:
        async_session (AsyncSession, required): SQLAlchemy async_session for database connection.
        request_id    (str         , required): ID of the request.
        id            (str         , required): ID of the task to get.
        warn_mode     (WarnEnum    , optional): Warning mode. Defaults to `WarnEnum.IGNORE`.

    Raises:
        BaseHTTPException: If task is not found.

    Returns:
        TaskORM: TaskORM model.
    """

    await async_log_mode(
        message=f"[{request_id}] - Getting task with '{id}' ID...",
        warn_mode=warn_mode,
    )

    _task_orm: TaskORM
    try:
        _task_orm: TaskORM = await TaskORM.async_get(async_session=async_session, id=id)

        await async_log_mode(
            message=f"[{request_id}] - Successfully retrieved task with '{id}' ID.",
            level="SUCCESS",
            warn_mode=warn_mode,
        )
    except NoResultFound:
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.NOT_FOUND,
            message=f"Not found task with '{id}' ID!",
        )

    return _task_orm


@validate_call(config={"arbitrary_types_allowed": True})
async def async_update(
    async_session: AsyncSession,
    request_id: str,
    id: str,
    auto_commit: bool = False,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
    **kwargs,
) -> TaskORM:
    """Update task by ID.

    Args:
        async_session (AsyncSession, required): SQLAlchemy async_session for database connection.
        request_id    (str         , required): ID of the request.
        id            (str         , required): ID of the task to update.
        auto_commit   (bool        , optional): Auto commit. Defaults to False.
        warn_mode     (WarnEnum    , optional): Warning mode. Defaults to `WarnEnum.IGNORE`.
        **kwargs      (dict        , required): Column and value as key-value pair for updating.

    Raises:
        BaseHTTPException: If no task data provided to update.
        BaseHTTPException: If task is not found.
        BaseHTTPException: If task data is missing.
        BaseHTTPException: If task reference data is invalid.

    Returns:
        TaskORM: Updated TaskORM object.
    """

    await async_log_mode(
        message=f"[{request_id}] - Updating task with '{id}' ID...",
        warn_mode=warn_mode,
    )

    _task_orm: TaskORM
    try:
        _task_orm: TaskORM = await TaskORM.async_update_by_id(
            async_session=async_session, id=id, auto_commit=auto_commit, **kwargs
        )

        await async_log_mode(
            message=f"[{request_id}] - Successfully updated task with '{id}' ID.",
            level="SUCCESS",
            warn_mode=warn_mode,
        )
    except EmptyValueError:
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.UNPROCESSABLE_ENTITY,
            message="No task data provided to update!",
        )
    except NoResultFound:
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.NOT_FOUND,
            message=f"Not found task with '{id}' ID!",
        )
    except NullConstraintError as err:
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.UNPROCESSABLE_ENTITY,
            message="Task data is missing!",
            description=f"Task: {err}",
        )

    return _task_orm


@validate_call(config={"arbitrary_types_allowed": True})
async def async_delete(
    async_session: AsyncSession,
    request_id: str,
    id: str,
    auto_commit: bool = False,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> None:
    """Delete task by ID.

    Args:
        async_session (AsyncSession, required): SQLAlchemy async_session for database connection.
        request_id    (str         , required): ID of the request.
        id            (str         , required): ID of the task to delete.
        auto_commit   (bool        , optional): Auto commit. Defaults to False.
        warn_mode     (WarnEnum    , optional): Warning mode. Defaults to `WarnEnum.IGNORE`.

    Raises:
        BaseHTTPException: If task is not found.
    """

    await async_log_mode(
        message=f"[{request_id}] - Deleting task with '{id}' ID...",
        warn_mode=warn_mode,
    )

    try:
        await TaskORM.async_delete_by_id(
            async_session=async_session, id=id, auto_commit=auto_commit
        )

        await async_log_mode(
            message=f"[{request_id}] - Successfully deleted task with '{id}' ID.",
            level="SUCCESS",
            warn_mode=warn_mode,
        )
    except NoResultFound:
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.NOT_FOUND,
            message=f"Not found task with '{id}' ID!",
        )

    return


__all__ = [
    "async_get_list",
    "async_create",
    "async_get",
    "async_update",
    "async_delete",
]
