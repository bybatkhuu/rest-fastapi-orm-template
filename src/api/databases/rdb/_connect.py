import asyncio

from pydantic import validate_call, AnyUrl
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    async_sessionmaker,
    async_scoped_session,
    AsyncSession,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool, QueuePool, SingletonThreadPool

from api.config import config


## Async
@validate_call
def make_async_engine(dsn_url: AnyUrl, **kwargs) -> AsyncEngine:
    """Create an async engine from a database connection string.

    Args:
        dsn_url  (AnyUrl        , required): Database connection string as Data Source Name (URL).
        **kwargs (Dict[str, Any], optional): Additional keyword arguments.

    Returns:
        AsyncEngine: SQLAlchemy async engine for database.
    """

    if not kwargs:
        kwargs = {}

    if ("connect_args" not in kwargs) and config.db.connect_args:
        kwargs["connect_args"] = config.db.connect_args

    if "echo" not in kwargs:
        kwargs["echo"] = config.db.echo_sql

    if "echo_pool" not in kwargs:
        kwargs["echo_pool"] = config.db.echo_pool

    if "pool_pre_ping" not in kwargs:
        kwargs["pool_pre_ping"] = True

    if "pool_recycle" not in kwargs:
        kwargs["pool_recycle"] = config.db.pool_recycle

    if "poolclass" not in kwargs:
        kwargs["poolclass"] = AsyncAdaptedQueuePool

    if issubclass(kwargs["poolclass"], AsyncAdaptedQueuePool):
        if "max_overflow" not in kwargs:
            kwargs["max_overflow"] = config.db.max_overflow

        if "pool_timeout" not in kwargs:
            kwargs["pool_timeout"] = config.db.pool_timeout

    if (
        issubclass(kwargs["poolclass"], AsyncAdaptedQueuePool)
        or issubclass(kwargs["poolclass"], SingletonThreadPool)
    ) and ("pool_size" not in kwargs):
        kwargs["pool_size"] = config.db.pool_size

    _dsn_url = str(dsn_url)
    _async_engine = create_async_engine(url=_dsn_url, **kwargs)
    return _async_engine


@validate_call(config={"arbitrary_types_allowed": True})
def create_async_session_maker(
    async_engine: AsyncEngine, **kwargs
) -> async_scoped_session[AsyncSession]:
    """Create an async session maker from an async engine.

    Args:
        async_engine (AsyncEngine   , required): SQLAlchemy async engine for session.
        **kwargs     (Dict[str, Any], optional): Additional keyword arguments.

    Returns:
        async_scoped_session[AsyncSession]: SQLAlchemy async session maker.
    """

    _async_session_factory = async_sessionmaker(
        bind=async_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        **kwargs
    )
    _AsyncSession = async_scoped_session(
        session_factory=_async_session_factory, scopefunc=asyncio.current_task
    )
    return _AsyncSession


## Sync
@validate_call
def make_engine(dsn_url: AnyUrl, **kwargs) -> Engine:
    """Create an engine from a database connection string.

    Args:
        dsn_url  (AnyUrl        , required): Database connection string as Data Source Name (URL).
        **kwargs (Dict[str, Any], optional): Additional keyword arguments.

    Returns:
        Engine: SQLAlchemy engine for database.
    """

    if not kwargs:
        kwargs = {}

    if ("connect_args" not in kwargs) and config.db.connect_args:
        kwargs["connect_args"] = config.db.connect_args

    if "echo" not in kwargs:
        kwargs["echo"] = config.db.echo_sql

    if "echo_pool" not in kwargs:
        kwargs["echo_pool"] = config.db.echo_pool

    if "pool_pre_ping" not in kwargs:
        kwargs["pool_pre_ping"] = True

    if "pool_recycle" not in kwargs:
        kwargs["pool_recycle"] = config.db.pool_recycle

    if "poolclass" not in kwargs:
        kwargs["poolclass"] = QueuePool

    if issubclass(kwargs["poolclass"], QueuePool):
        if "max_overflow" not in kwargs:
            kwargs["max_overflow"] = config.db.max_overflow

        if "pool_timeout" not in kwargs:
            kwargs["pool_timeout"] = config.db.pool_timeout

    if (
        issubclass(kwargs["poolclass"], QueuePool)
        or issubclass(kwargs["poolclass"], SingletonThreadPool)
    ) and ("pool_size" not in kwargs):
        kwargs["pool_size"] = config.db.pool_size

    _dsn_url = str(dsn_url)
    _engine = create_engine(url=_dsn_url, **kwargs)
    return _engine


@validate_call(config={"arbitrary_types_allowed": True})
def create_session_maker(engine: Engine, **kwargs) -> scoped_session[Session]:
    """Create a session maker from an engine.

    Args:
        engine (Engine, required): SQLAlchemy engine for session.

    Returns:
        scoped_session[Session]: SQLAlchemy session maker.
    """

    _session_factory = sessionmaker(
        bind=engine, autocommit=False, autoflush=False, expire_on_commit=False, **kwargs
    )
    _Session = scoped_session(session_factory=_session_factory)
    return _Session


__all__ = [
    "make_async_engine",
    "create_async_session_maker",
    "make_engine",
    "create_session_maker",
]
