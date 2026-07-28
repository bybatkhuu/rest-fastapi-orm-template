# flake8: noqa

from api.config import config
from api.externals.db import (
    init_table_prefix,
    async_is_db_connectable,
    async_check_db,
    async_close_db,
    check_db,
    make_async_engine,
    make_engine,
    create_async_session_maker,
    BaseORM,
    AsyncBaseORM,
    SyncBaseORM,
)

init_table_prefix(table_prefix=config.db.prefix)

assert config.db.dsn_url is not None, "DB_DSN_URL should always be configured!"
assert (
    config.db.read_dsn_url is not None
), "DB_READ_DSN_URL should always be configured!"


## Async
async_write_engine = make_async_engine(
    dsn_url=config.db.dsn_url.get_secret_value(),
    connect_args=config.db.connect_args,
    echo=config.db.echo_sql,
    echo_pool=config.db.echo_pool,
    pool_recycle=config.db.pool_recycle,
    max_overflow=config.db.max_overflow,
    pool_timeout=config.db.pool_timeout,
    pool_size=config.db.pool_size,
)
AsyncWriteSession = create_async_session_maker(async_engine=async_write_engine)

async_read_engine = make_async_engine(
    dsn_url=config.db.read_dsn_url.get_secret_value(),
    connect_args=config.db.connect_args,
    echo=config.db.echo_sql,
    echo_pool=config.db.echo_pool,
    pool_recycle=config.db.pool_recycle,
    max_overflow=config.db.max_overflow,
    pool_timeout=config.db.pool_timeout,
    pool_size=config.db.pool_size,
)
AsyncReadSession = create_async_session_maker(async_engine=async_read_engine)

## Sync
# write_engine = make_engine(
#     dsn_url=config.db.dsn_url.get_secret_value(),
#     connect_args=config.db.connect_args,
#     echo=config.db.echo_sql,
#     echo_pool=config.db.echo_pool,
#     pool_recycle=config.db.pool_recycle,
#     max_overflow=config.db.max_overflow,
#     pool_timeout=config.db.pool_timeout,
#     pool_size=config.db.pool_size,
# )
# WriteSession = create_session_maker(engine=write_engine)

# read_engine = make_engine(
#     dsn_url=config.db.read_dsn_url.get_secret_value(),
#     connect_args=config.db.connect_args,
#     echo=config.db.echo_sql,
#     echo_pool=config.db.echo_pool,
#     pool_recycle=config.db.pool_recycle,
#     max_overflow=config.db.max_overflow,
#     pool_timeout=config.db.pool_timeout,
#     pool_size=config.db.pool_size,
# )
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


def register_orms() -> None:
    # Add all your ORM models here...
    from api.resources.table_stat.model import TableStatORM  # noqa: F401
    from api.resources.scope.model import ScopeORM  # noqa: F401
    from api.resources.role.model import RoleORM  # noqa: F401
    from api.resources.role_scope.model import RoleScopeORM  # noqa: F401
    from api.resources.user.model import UserORM  # noqa: F401
    from api.resources.user_role.model import UserRoleORM  # noqa: F401
    from api.resources.user_token.model import UserTokenORM  # noqa: F401
    from api.resources.user_api_key.model import UserApiKeyORM  # noqa: F401

    # from api.resources.auth_audit_log.model import AuthAuditLogORM  # noqa: F401

    return


__all__ = [
    "async_is_db_connectable",
    "async_check_db",
    "async_close_db",
    "check_db",
    "make_async_engine",
    "make_engine",
    "create_async_session_maker",
    "async_write_engine",
    "async_read_engine",
    "AsyncWriteSession",
    "AsyncReadSession",
    # "write_engine",
    # "read_engine",
    # "WriteSession",
    # "ReadSession",
    "engines",
    "sessions",
    "register_orms",
    "BaseORM",
    "AsyncBaseORM",
    "SyncBaseORM",
]
