from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response

from api.core.utils import is_browser


class DetectBrowserMiddleware(BaseHTTPMiddleware):
    """Detect if the request is from a browser or not.

    Inherits:
        BaseHTTPMiddleware: Base HTTP middleware from Starlette.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request.state.is_browser = is_browser(request)
        response: Response = await call_next(request)
        return response


__all__ = ["DetectBrowserMiddleware"]
