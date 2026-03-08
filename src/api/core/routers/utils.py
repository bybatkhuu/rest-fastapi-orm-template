from fastapi import APIRouter, Request

from api.core.schemas import BaseResPM
from api.core.responses import BaseResponse
from api.databases.rdb import async_is_db_connectable, async_read_engine

router = APIRouter(tags=["Utils"])


@router.get(
    "/",
    summary="Base",
    description="Base path for all API endpoints.",
    response_model=BaseResPM,
)
async def get_base(request: Request):
    return BaseResponse(request=request, message="Welcome to the REST API service!")


@router.get(
    "/ping",
    summary="Ping",
    description="Check if the service is up and running.",
    response_model=BaseResPM,
)
async def get_ping(request: Request):
    return BaseResponse(
        request=request, message="Pong!", headers={"Cache-Control": "no-cache"}
    )


@router.get(
    "/health",
    summary="Health",
    description="Check health of all related backend services.",
    response_model=BaseResPM,
)
async def get_health(request: Request):
    _message = "Everything is OK."
    _data = {
        "api": {"message": "API is up.", "is_alive": True},
        "db": {"message": "Database status is unknown.", "is_alive": None},
    }
    _status_code = 200

    if await async_is_db_connectable(async_engine=async_read_engine):
        _data["db"] = {"message": "Database is connected.", "is_alive": True}
    else:
        _status_code = 503
        _message = "One or more services are unavailable!"
        _data["db"] = {"message": "Database connection failed!", "is_alive": False}

    return BaseResponse(
        request=request,
        status_code=_status_code,
        message=_message,
        content=_data,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


__all__ = ["router"]
