from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from potato_util.io import async_create_dir
from potato_util.crypto import asymmetric as asymmetric_utils

from api.__version__ import __version__
from api.config import config
from api.database import (
    async_check_db,
    async_close_db,
    async_write_engine,
    async_read_engine,
    engines,
    sessions,
    register_orms,
)
from api.logger import logger


async def _async_create_dirs() -> None:
    """Create directories before starting FastAPI application.

    Raises:
        SystemExit: If failed to create directories.
    """

    try:
        await async_create_dir(config.api.paths.data_dir)
        # Add directories that need to be created here...

    except Exception:
        logger.exception("Failed to create directories:")
        raise SystemExit(1)

    return


async def _async_ensure_asymmetric_keys() -> None:
    """Ensure asymmetric keys exist when asymmetric keys are set to be generated.

    Raises:
        SystemExit: If failed to create asymmetric keys.
    """

    try:
        await asymmetric_utils.async_create_keys(
            asymmetric_keys_dir=config.api.paths.asymmetric_keys_dir,
            key_size=config.api.security.asymmetric.key_size,
            private_key_fname=config.api.security.asymmetric.private_key_fname,
            public_key_fname=config.api.security.asymmetric.public_key_fname,
        )
    except Exception:
        logger.exception("Failed to create asymmetric keys:")
        raise SystemExit(1)

    return


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for FastAPI application.
    Startup and shutdown events are logged.

    Args:
        app (FastAPI, required): FastAPI application instance.
    """

    logger.info("Preparing to startup...")
    await _async_create_dirs()
    if config.api.security.asymmetric.generate:
        await _async_ensure_asymmetric_keys()

    await async_check_db(
        async_engine=async_write_engine,
        max_try_connect=config.db.max_try_connect,
        retry_after=config.db.retry_after,
    )
    await async_check_db(
        async_engine=async_read_engine,
        is_write_db=False,
        max_try_connect=config.db.max_try_connect,
        retry_after=config.db.retry_after,
    )
    register_orms()

    # Add startup code here...
    logger.success("Finished preparation to startup.")
    logger.opt(colors=True).info(f"Version: <c>{__version__}</c>")
    logger.opt(colors=True).info(f"API version: <c>{config.api.version}</c>")
    logger.opt(colors=True).info(f"API prefix: <c>{config.api.prefix}</c>")
    logger.opt(colors=True).info(
        f"Listening on: <c>{config.api.http_scheme}://{config.api.bind_host}:{config.api.port}</c>"
    )

    yield

    logger.info("Preparing to shutdown...")
    # Add shutdown code here...
    await async_close_db(sessions=sessions, engines=engines)
    logger.success("Finished preparation to shutdown.")


__all__ = [
    "lifespan",
]
