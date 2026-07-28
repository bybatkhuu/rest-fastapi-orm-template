from fastapi import Request
from fastapi.exceptions import RequestValidationError

from potato_util.constants import EnvEnum

from api.core.exceptions.http import UnprocessableEntityError
from api.core.responses import BaseResponse
from api.config import config


# For RequestValidationError error:
async def validation_error_handler(
    request: Request, exc: RequestValidationError | Exception
) -> BaseResponse:
    """RequestValidationError handler for validation error.

    Args:
        request (Request               , required): Request object from FastAPI.
        exc     (RequestValidationError, required): RequestValidationError object from FastAPI.

    Returns:
        BaseResponse: Response object.
    """

    assert isinstance(
        exc, RequestValidationError
    ), f"`exc` argument type is invalid {type(exc)}, expected <RequestValidationError>!"

    _message = "Validation error!"
    _error_dict = UnprocessableEntityError.error.model_dump(mode="json")
    _error_dict["description"] = _message
    if (config.env != EnvEnum.STAGING) and (config.env != EnvEnum.PRODUCTION):
        _error_dict["description"] = str(exc)

    _details = exc.errors()
    for _detail in _details:
        if ("ctx" in _detail) and ("error" in _detail["ctx"]):
            _detail["ctx"]["error"] = str(_detail["ctx"]["error"])

    _error_dict["detail"] = _details

    return BaseResponse(
        request=request, status_code=422, message=_message, error=_error_dict
    )


__all__ = ["validation_error_handler"]
