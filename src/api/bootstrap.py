# Standard libraries
from typing import Any
from collections.abc import Callable

# Third-party libraries
import uvicorn
from uvicorn._types import ASGIApplication
from pydantic import validate_call
from fastapi import FastAPI

from beans_logging_fastapi import add_logger

# Internal modules
from api.__version__ import __version__
from api.config import config
from api.helpers.ssl import check_ssl_certs
from api.lifespan import lifespan
from api.middleware import add_middlewares
from api.router import add_routers
from api.mount import add_mounts
from api.exception import add_exception_handlers
from api.core.responses import BaseResponse


def _pre_init() -> None:
    """Pre-initialization tasks before creating FastAPI application."""

    if config.api.security.ssl.generate or config.api.security.ssl.enabled:
        check_ssl_certs()

    # Add more pre-initialization tasks here...

    return


def create_app() -> FastAPI:
    """Create FastAPI application instance.

    Returns:
        FastAPI: FastAPI application instance.
    """

    _pre_init()

    app = FastAPI(
        title=config.api.title,
        version=__version__,
        lifespan=lifespan,
        default_response_class=BaseResponse,
        **config.api.docs.model_dump(exclude={"enabled", "scalar_url"}),
    )

    add_logger(
        app=app,
        config=config.api.logger,
        has_proxy_headers=config.api.uvicorn.proxy_headers,
    )

    add_middlewares(app=app)
    add_routers(app=app)
    add_mounts(app=app)
    add_exception_handlers(app=app)

    return app


@validate_call(config={"arbitrary_types_allowed": True})
def run_server(app: FastAPI | ASGIApplication | Callable[..., Any] | str) -> None:
    """Run uvicorn server.

    Args:
        app (FastAPI            |
             ASGIApplication    |
             Callable[..., Any] |
             str                 , required): FastAPI application instance or ASGI application or import string.
    """

    uvicorn.run(
        app=app,
        host=config.api.bind_host,
        port=config.api.port,
        **config.api.uvicorn.model_dump(),
    )

    return


__all__ = [
    "create_app",
    "run_server",
]
