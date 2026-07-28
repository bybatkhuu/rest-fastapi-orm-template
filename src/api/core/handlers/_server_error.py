from fastapi import Request

from beans_logging_fastapi import log_http_error

from api.core.exceptions.http import InternalServerError, DBPkError, DBUqError
from api.externals.db.models.exceptions import PrimaryKeyError, UniqueKeyError
from api.config import config
from api.core.responses import BaseResponse

# from api.logger import logger


# For unhandled Exception or 500 internal server error:
async def server_error_handler(request: Request, exc: Exception) -> BaseResponse:
    """Error handler for any kind of unhandled Exception or 500 internal server error.

    Args:
        request (Request  , required): Request object from FastAPI.
        exc     (Exception, required): Any kind of Exception object.

    Returns:
        BaseResponse: Response object.
    """

    _error_pm = InternalServerError.error.model_copy(deep=True)
    if isinstance(exc, PrimaryKeyError):
        _error_pm = DBPkError.error.model_copy(deep=True)
    if isinstance(exc, UniqueKeyError):
        _error_pm = DBUqError.error.model_copy(deep=True)

    _exc_str = str(exc)
    _status_code = _error_pm.status_code
    _error_dict = _error_pm.model_dump(mode="json")
    _error_dict["detail"] = _exc_str
    _message: str = _error_dict.get("message", "Internal Server Error")

    # logger.exception(f"{_error_pm.code} - {_exc_str}")
    log_http_error(
        request=request,
        status_code=_status_code,
        exc=exc,
        sub_format=config.api.logger.http.std.err_sub_format,
    )
    return BaseResponse(
        request=request, status_code=_status_code, message=_message, error=_error_dict
    )


__all__ = ["server_error_handler"]
