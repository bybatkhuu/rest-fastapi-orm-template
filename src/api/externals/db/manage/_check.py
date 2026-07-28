import time
import asyncio

from pydantic import validate_call
from sqlalchemy import Engine, Result, text
from sqlalchemy.ext.asyncio import AsyncEngine

from potato_util.constants import WarnEnum
from beans_logging import logger

from ._create import async_create_db, create_db


# Async
@validate_call(config={"arbitrary_types_allowed": True})
async def async_is_db_connectable(async_engine: AsyncEngine) -> bool:
    """Check if the database is connectable.

    Args:
        async_engine (AsyncEngine, required): SQLAlchemy async engine to check connection.

    Returns:
        bool: True if the database is connectable, False otherwise.
    """

    _is_connectable = False
    try:
        async with async_engine.connect() as _connection:
            _result: Result = await _connection.execute(text("SELECT 1"))
            _is_connectable = bool(_result.scalar())
    except Exception:  # nosec B110
        pass
    finally:
        await async_engine.dispose()

    return _is_connectable


@validate_call(config={"arbitrary_types_allowed": True})
async def async_check_db(
    async_engine: AsyncEngine,
    is_write_db: bool = True,
    max_try_connect: int = 3,
    retry_after: int = 5,
) -> bool:
    """Check database connection, exit application if failed after few attempts.

    Args:
        async_engine    (AsyncEngine, required): SQLAlchemy async engine to check connection.
        is_write_db     (bool       , optional): If True, create database if it doesn't exist. Defaults to True.
        max_try_connect (int        , optional): Maximum number of connection attempts. Defaults to 3.
        retry_after     (int        , optional): Number of seconds to wait before retrying. Defaults to 5.

    Returns:
        bool: True if the database is exists and connectable, False otherwise.
    """

    _is_done = False
    _tmp_str = "" if is_write_db else "read "
    _db_name = async_engine.url.database
    logger.info(f"Connecting to the '{_db_name}' {_tmp_str}database...")
    for _i in range(max_try_connect):
        # logger.debug(f"Trying to connect '{_db_name}' {_tmp_str}database {_i + 1} time(s)...")

        if is_write_db:
            await async_create_db(async_engine=async_engine, warn_mode=WarnEnum.IGNORE)

        if await async_is_db_connectable(async_engine=async_engine):
            _is_done = True
            break
        else:
            if (max_try_connect - 1) <= _i:
                _message = f"Falied to connect '{_db_name}' {_tmp_str}database {_i + 1} time(s)!"
                try:
                    raise ConnectionError(_message)
                except Exception:
                    logger.exception(_message)
                    raise SystemExit(2)

            logger.warning(
                f"Unable to connect '{_db_name}' {_tmp_str}database {_i + 1} time(s), "
                f"retrying in {retry_after} second(s)..."
            )
            await asyncio.sleep(retry_after)

    logger.success(f"Successfully connected to the '{_db_name}' {_tmp_str}database.")
    return _is_done


# Sync
@validate_call(config={"arbitrary_types_allowed": True})
def is_db_connectable(engine: Engine) -> bool:
    """Check if the database is connectable.

    Args:
        engine (Engine, required): SQLAlchemy engine to check connection.

    Returns:
        bool: True if the database is connectable, False otherwise.
    """

    _is_connectable = False
    try:
        with engine.connect() as _connection:
            _result: Result = _connection.execute(text("SELECT 1"))
            _is_connectable = bool(_result.scalar())
    except Exception:  # nosec B110
        pass
    finally:
        engine.dispose()

    return _is_connectable


@validate_call(config={"arbitrary_types_allowed": True})
def check_db(
    engine: Engine,
    is_write_db: bool = True,
    max_try_connect: int = 3,
    retry_after: int = 5,
) -> bool:
    """Check database connection, exit application if failed after few attempts.

    Args:
        engine          (Engine, required): SQLAlchemy engine to check connection.
        is_write_db     (bool  , optional): If True, create database if it doesn't exist. Defaults to True.
        max_try_connect (int   , optional): Maximum number of connection attempts. Defaults to 3.
        retry_after     (int   , optional): Number of seconds to wait before retrying. Defaults to 5.

    Returns:
        bool: True if the database is exists and connectable, False otherwise.
    """

    _is_done = False
    _tmp_str = "" if is_write_db else "read "
    _db_name = engine.url.database
    logger.info(f"Connecting to the '{_db_name}' {_tmp_str}database...")
    for _i in range(max_try_connect):
        # logger.debug(f"Trying to connect '{_db_name}' {_tmp_str}database {_i + 1} time(s)...")

        if is_write_db:
            create_db(engine=engine, warn_mode=WarnEnum.IGNORE)

        if is_db_connectable(engine=engine):
            _is_done = True
            break
        else:
            if (max_try_connect - 1) <= _i:
                _message = f"Falied to connect '{_db_name}' {_tmp_str}database {_i + 1} time(s)!"
                try:
                    raise ConnectionError(_message)
                except Exception:
                    logger.exception(_message)
                    raise SystemExit(2)

            logger.warning(
                f"Unable to connect '{_db_name}' {_tmp_str}database {_i + 1} time(s), "
                f"retrying in {retry_after} second(s)..."
            )
            time.sleep(retry_after)

    logger.success(f"Successfully connected to the '{_db_name}' {_tmp_str}database.")
    return _is_done


__all__ = [
    "async_is_db_connectable",
    "async_check_db",
    "is_db_connectable",
    "check_db",
]
