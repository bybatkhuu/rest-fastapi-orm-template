import asyncio
from typing import Any

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
from sqlalchemy.pool import (
    AsyncAdaptedQueuePool,
    QueuePool,
    SingletonThreadPool,
    NullPool,
    Pool,
)


# Async
@validate_call
def make_async_engine(
    dsn_url: AnyUrl | str,
    connect_args: dict[str, Any] | None = {"sslmode": "prefer"},
    echo: bool | str = False,
    echo_pool: bool | str = False,
    pool_pre_ping: bool = True,
    pool_recycle: int = 10800,
    poolclass: (
        type[AsyncAdaptedQueuePool]
        | type[SingletonThreadPool]
        | type[NullPool]
        | type[Pool]
    ) = AsyncAdaptedQueuePool,
    max_overflow: int = 10,
    pool_timeout: int = 30,
    pool_size: int = 10,
    **kwargs,
) -> AsyncEngine:
    """Create an async engine from a database connection string.

    Args:
        dsn_url  (AnyUrl | str  , required): Database connection string as Data Source Name (URL).
        **kwargs (dict[str, Any], optional): Additional keyword arguments.

    Returns:
        AsyncEngine: SQLAlchemy async engine for database.
    """

    if not kwargs:
        kwargs = {}

    if connect_args:
        kwargs["connect_args"] = connect_args

    kwargs["echo"] = echo
    kwargs["echo_pool"] = echo_pool
    kwargs["pool_pre_ping"] = pool_pre_ping
    kwargs["pool_recycle"] = pool_recycle
    kwargs["poolclass"] = poolclass

    if issubclass(kwargs["poolclass"], AsyncAdaptedQueuePool):
        kwargs["max_overflow"] = max_overflow
        kwargs["pool_timeout"] = pool_timeout

    if issubclass(kwargs["poolclass"], AsyncAdaptedQueuePool) or issubclass(
        kwargs["poolclass"], SingletonThreadPool
    ):
        kwargs["pool_size"] = pool_size

    if isinstance(dsn_url, AnyUrl):
        dsn_url = str(dsn_url)

    _async_engine = create_async_engine(url=dsn_url, **kwargs)
    return _async_engine


@validate_call(config={"arbitrary_types_allowed": True})
def create_async_session_maker(
    async_engine: AsyncEngine, **kwargs
) -> async_scoped_session[AsyncSession]:
    """Create an async session maker from an async engine.

    Args:
        async_engine (AsyncEngine   , required): SQLAlchemy async engine for session.
        **kwargs     (dict[str, Any], optional): Additional keyword arguments.

    Returns:
        async_scoped_session[AsyncSession]: SQLAlchemy async session maker.
    """

    _async_session_factory = async_sessionmaker(
        bind=async_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        **kwargs,
    )
    _AsyncSession = async_scoped_session(
        session_factory=_async_session_factory, scopefunc=asyncio.current_task
    )
    return _AsyncSession


# Sync
@validate_call
def make_engine(
    dsn_url: AnyUrl | str,
    connect_args: dict[str, Any] | None = {"sslmode": "prefer"},
    echo: bool | str = False,
    echo_pool: bool | str = False,
    pool_pre_ping: bool = True,
    pool_recycle: int = 10800,
    poolclass: (
        type[QueuePool] | type[SingletonThreadPool] | type[NullPool] | type[Pool]
    ) = QueuePool,
    max_overflow: int = 10,
    pool_timeout: int = 30,
    pool_size: int = 10,
    **kwargs,
) -> Engine:
    """Create an engine from a database connection string.

    Args:
        dsn_url  (AnyUrl | str  , required): Database connection string as Data Source Name (URL).
        **kwargs (dict[str, Any], optional): Additional keyword arguments.

    Returns:
        Engine: SQLAlchemy engine for database.
    """

    if not kwargs:
        kwargs = {}

    if connect_args:
        kwargs["connect_args"] = connect_args

    kwargs["echo"] = echo
    kwargs["echo_pool"] = echo_pool
    kwargs["pool_pre_ping"] = pool_pre_ping
    kwargs["pool_recycle"] = pool_recycle
    kwargs["poolclass"] = poolclass

    if issubclass(kwargs["poolclass"], QueuePool):
        kwargs["max_overflow"] = max_overflow
        kwargs["pool_timeout"] = pool_timeout

    if issubclass(kwargs["poolclass"], QueuePool) or issubclass(
        kwargs["poolclass"], SingletonThreadPool
    ):
        kwargs["pool_size"] = pool_size

    if isinstance(dsn_url, AnyUrl):
        dsn_url = str(dsn_url)

    _engine = create_engine(url=dsn_url, **kwargs)
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
