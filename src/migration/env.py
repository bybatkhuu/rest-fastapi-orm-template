from logging.config import fileConfig

# from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from dotenv import load_dotenv

load_dotenv(override=True)

from api.config import config as api_config  # noqa: E402
from api.database import make_engine, check_db, register_orms, BaseORM  # noqa: E402

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
# target_metadata = None
register_orms()
target_metadata = [BaseORM.metadata]

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """

    # url = config.get_main_option("sqlalchemy.url")

    assert (
        api_config.db.dsn_url is not None
    ), "Database DSN URL must be provided in the configuration!"

    _url = api_config.db.dsn_url.get_secret_value()
    context.configure(
        url=_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

    return


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """

    # connectable = engine_from_config(
    #     config.get_section(config.config_ini_section, {}),
    #     prefix="sqlalchemy.",
    #     poolclass=pool.NullPool,
    # )

    assert (
        api_config.db.dsn_url is not None
    ), "Database DSN URL must be provided in the configuration!"

    _engine = make_engine(
        dsn_url=api_config.db.dsn_url.get_secret_value(),
        connect_args=api_config.db.connect_args,
        echo=api_config.db.echo_sql,
        echo_pool=api_config.db.echo_pool,
        pool_recycle=api_config.db.pool_recycle,
        poolclass=pool.NullPool,
        max_overflow=api_config.db.max_overflow,
        pool_timeout=api_config.db.pool_timeout,
        pool_size=api_config.db.pool_size,
    )
    check_db(
        engine=_engine,
        max_try_connect=api_config.db.max_try_connect,
        retry_after=api_config.db.retry_after,
    )
    with _engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_server_default=True,
            version_table=f"{api_config.db.prefix}alembic_version",
        )

        with context.begin_transaction():
            context.run_migrations()

    return


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
