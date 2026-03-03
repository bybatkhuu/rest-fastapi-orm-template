from typing import AsyncGenerator

# from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from api.databases.rdb import (
    AsyncWriteSession,
    AsyncReadSession,
    # WriteSession,
    # ReadSession,
)


async def async_get_write() -> AsyncGenerator[AsyncSession, None]:
    """Get write async database session.

    Yields:
        AsyncGenerator[AsyncSession, None]: SQLAlchemy async session.
    """

    # async with AsyncWriteSession() as _async_write_session:
    #     yield _async_write_session

    _async_write_session: AsyncSession = AsyncWriteSession()
    try:
        yield _async_write_session
    finally:
        await _async_write_session.close()


async def async_get_read() -> AsyncGenerator[AsyncSession, None]:
    """Get read async database session.

    Yields:
        AsyncGenerator[AsyncSession, None]: SQLAlchemy async session.
    """

    # async with AsyncReadSession() as _async_read_session:
    #     yield _async_read_session

    _async_read_session: AsyncSession = AsyncReadSession()
    try:
        yield _async_read_session
    finally:
        await _async_read_session.close()


# def get_write() -> Session:
#     """Get write database session.

#     Yields:
#         Iterator[Session]: SQLAlchemy session.
#     """

#     # with WriteSession() as _write_session:
#     #     yield _write_session

#     _write_session: Session = WriteSession()
#     try:
#         yield _write_session
#     finally:
#         _write_session.close()


# def get_read() -> Session:
#     """Get read database session.

#     Yields:
#         Iterator[Session]: SQLAlchemy session.
#     """

#     # with ReadSession() as _read_session:
#     #     yield _read_session

#     _read_session: Session = ReadSession()
#     try:
#         yield _read_session
#     finally:
#         _read_session.close()


__all__ = [
    "async_get_write",
    "async_get_read",
    # "get_write",
    # "get_read",
]
