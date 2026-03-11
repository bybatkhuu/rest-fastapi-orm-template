from pydantic import validate_call
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import Engine, URL
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy_utils import database_exists, create_database

from potato_util.constants import WarnEnum

from api.core.models import BaseORM
from api.logger import logger


def register_orms() -> None:
    # Add all your ORM models here...
    from api.endpoints.table_stat.model import TableStatORM  # noqa: F401
    from api.endpoints.task.model import TaskORM  # noqa: F401

    return


# Async
@validate_call(config={"arbitrary_types_allowed": True})
async def async_create_db(
    async_engine: AsyncEngine, warn_mode: WarnEnum = WarnEnum.ERROR
) -> bool:
    """Create database if it doesn't exist.

    Args:
        async_engine (AsyncEngine, required): SQLAlchemy async engine to create database.
        warn_mode    (WarnEnum   , optional): Warning mode. Defaults to WarnEnum.ERROR.

    Raises:
        Exception: If can't create/connect database and `warn_mode` is set to WarnEnum.ERROR.

    Returns:
        bool: True if the database exists, False otherwise.
    """

    _is_db_exists = False
    _url: URL = async_engine.url
    try:
        if not await run_in_threadpool(database_exists, url=_url):
            logger.warning(
                f"Can't connect to '{_url.database}' database or doesn't exist, trying to create it..."
            )
            await run_in_threadpool(create_database, url=_url)
            logger.success(f"Successfully created '{_url.database}' database.")

        _is_db_exists = True
    except Exception:
        _message = f"Failed to create '{_url.database}' database!"
        if warn_mode == WarnEnum.ALWAYS:
            logger.error(_message)
        elif warn_mode == WarnEnum.DEBUG:
            logger.debug(_message)
        elif warn_mode == WarnEnum.ERROR:
            raise

    return _is_db_exists


@validate_call(config={"arbitrary_types_allowed": True})
async def async_create_structure(async_engine: AsyncEngine) -> None:
    """Initialize and create database structure.

    Args:
        async_engine (AsyncEngine, required): SQLAlchemy async engine to initialize database structure.
    """

    _db_name = async_engine.url.database
    logger.info(f"Initializing '{_db_name}' database structure...")
    try:
        async with async_engine.begin() as _connection:
            register_orms()
            await _connection.run_sync(BaseORM.metadata.create_all)

    except Exception:
        await async_engine.dispose()
        logger.error(f"Failed to create '{_db_name}' database structure!")
        raise

    finally:
        await async_engine.dispose()
    logger.success(f"Successfully initialized '{_db_name}' database structure.")


# Sync
@validate_call(config={"arbitrary_types_allowed": True})
def create_db(engine: Engine, warn_mode: WarnEnum = WarnEnum.ERROR) -> bool:
    """Create database if it doesn't exist.

    Args:
        engine    (Engine  , required): SQLAlchemy engine to create database.
        warn_mode (WarnEnum, optional): Warning mode. Defaults to WarnEnum.ERROR.

    Raises:
        Exception: If can't create/connect database and `warn_mode` is set to WarnEnum.ERROR.

    Returns:
        bool: True if the database exists, False otherwise.
    """

    _is_db_exists = False
    _url: URL = engine.url
    try:
        if not database_exists(url=_url):
            logger.warning(
                f"Can't connect to '{_url.database}' database or doesn't exist, trying to create it..."
            )
            create_database(url=_url)
            logger.success(f"Successfully created '{_url.database}' database.")

        _is_db_exists = True
    except Exception:
        _message = f"Failed to create '{_url.database}' database!"
        if warn_mode == WarnEnum.ALWAYS:
            logger.error(_message)
        elif warn_mode == WarnEnum.DEBUG:
            logger.debug(_message)
        elif warn_mode == WarnEnum.ERROR:
            raise

    return _is_db_exists


@validate_call(config={"arbitrary_types_allowed": True})
def create_structure(engine: Engine) -> None:
    """Initialize and create database structure.

    Args:
        engine (Engine, required): SQLAlchemy engine to initialize database structure.
    """

    _db_name = engine.url.database
    logger.info(f"Initializing '{_db_name}' database structure...")
    try:
        with engine.begin() as _connection:
            register_orms()
            BaseORM.metadata.create_all(bind=_connection)

    except Exception:
        engine.dispose()
        logger.error(f"Failed to create '{_db_name}' database structure!")
        raise

    finally:
        engine.dispose()
    logger.success(f"Successfully initialized '{_db_name}' database structure.")


__all__ = [
    "register_orms",
    "async_create_db",
    "async_create_structure",
    "create_structure",
    "create_db",
]
