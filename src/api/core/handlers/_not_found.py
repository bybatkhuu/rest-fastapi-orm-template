from fastapi import HTTPException, Request

from api.core.exceptions.http import NotFoundError
from api.core.responses import BaseResponse


# For 404 status code:
async def not_found_handler(
    request: Request, exc: HTTPException | Exception
) -> BaseResponse:
    """404 status code handler.

    Args:
        request (Request      , required): Request object from FastAPI.
        exc     (HTTPException, required): HTTPException object from FastAPI.

    Returns:
        BaseResponse: Response object.
    """

    if not isinstance(exc, HTTPException):
        exc = HTTPException(status_code=404)

    _error_dict = NotFoundError.error.model_dump(mode="json")
    _message: str = _error_dict.get("message", "Not Found")

    if hasattr(exc, "detail") and isinstance(exc.detail, dict):
        _message = exc.detail.get("message", _message)
        _error_dict = exc.detail.get("error", _error_dict)

    return BaseResponse(
        request=request, status_code=404, message=_message, error=_error_dict
    )


__all__ = ["not_found_handler"]
