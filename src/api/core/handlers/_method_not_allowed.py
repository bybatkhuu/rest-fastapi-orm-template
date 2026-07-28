from fastapi import HTTPException, Request

from api.core.exceptions.http import MethodNotAllowedError
from api.core.responses import BaseResponse


# For 405 status code:
async def method_not_allowed_handler(
    request: Request, exc: HTTPException | Exception
) -> BaseResponse:
    """405 status code handler.

    Args:
        request (Request      , required): Request object from FastAPI.
        exc     (HTTPException, required): HTTPException object from FastAPI.

    Returns:
        BaseResponse: Response object.
    """

    _error_dict = MethodNotAllowedError.error.model_dump(mode="json")
    _message: str = _error_dict.get("message", "Method Not Allowed")

    return BaseResponse(
        request=request, status_code=405, message=_message, error=_error_dict
    )


__all__ = ["method_not_allowed_handler"]
