from api.config import config

from ._connect import *
from ._check import *
from ._create import *
from ._close import *

register_orms()

## Async
async_write_engine = make_async_engine(dsn_url=config.db.dsn_url.get_secret_value())
AsyncWriteSession = create_async_session_maker(async_engine=async_write_engine)

async_read_engine = make_async_engine(dsn_url=config.db.read_dsn_url.get_secret_value())
AsyncReadSession = create_async_session_maker(async_engine=async_read_engine)

## Sync
# write_engine = make_engine(dsn_url=config.db.dsn_url.get_secret_value())
# WriteSession = create_session_maker(engine=write_engine)

# read_engine = make_engine(dsn_url=config.db.read_dsn_url.get_secret_value())
# ReadSession = create_session_maker(engine=read_engine)


engines = [
    async_write_engine,
    async_read_engine,
    # write_engine,
    # read_engine,
]
sessions = [
    AsyncWriteSession,
    AsyncReadSession,
    # WriteSession,
    # ReadSession,
]


__all__ = [
    "async_write_engine",
    "async_read_engine",
    "AsyncWriteSession",
    "AsyncReadSession",
    # "write_engine",
    # "WriteSession",
    # "read_engine",
    # "ReadSession",
    "engines",
    "sessions",
    "make_async_engine",
    "create_async_session_maker",
    "async_create_db",
    "async_is_db_connectable",
    "async_check_db",
    "async_create_structure",
    "async_close_db",
    "make_engine",
    "create_session_maker",
    "create_db",
    "is_db_connectable",
    "check_db",
    "create_structure",
    "close_db",
]
