from typing import Any, cast

from fastapi import (
    APIRouter,
    Request,
    HTTPException,
    Depends,
    Security,
    Path,
    Body,
    Query,
)
from sqlalchemy.ext.asyncio import AsyncSession

from potato_util.constants import ALPHANUM_HYPHEN_REGEX
from potato_util.http.fastapi import get_relative_url

from api.core.exceptions import http as http_errors
from api.core.dependencies import db as db_deps
from api.core.responses import BaseResponse
from api.resources.auth import dependencies as auth_deps
from api.config import config
from api.logger import Logger

from .schemas import (
    ApiKeyInPM,
    ApiKeyUpPM,
    ResApiKeyPM,
    ResApiKeysPM,
    ResCreatedApiKeyPM,
    ApiKeyStatusUpEnum,
)
from .model import UserApiKeyORM
from . import service

_RESOURCE_NAME = "me:api-keys"
router = APIRouter(prefix="/users/me/api-keys", tags=["API Keys"])


@router.get(
    "/",
    summary="Get API Key List",
    response_model=ResApiKeysPM,
    responses={401: {}, 403: {}, 422: {}},
)
async def get_api_keys(
    request: Request,
    skip: int = Query(
        default=0,
        ge=0,
        title="Skip",
        description="Number of data to skip.",
        examples=[0],
    ),
    limit: int = Query(
        default=config.db.select_limit,
        ge=1,
        le=config.db.select_max_limit,
        title="Limit",
        description="Limit of data list.",
        examples=[100],
    ),
    is_desc: bool = Query(
        default=config.db.select_is_desc,
        title="Sort Direction",
        description="Is sort descending or ascending.",
        examples=[True],
    ),
    key_prefix: str | None = Query(
        default=None,
        min_length=2,
        max_length=16,
        pattern=ALPHANUM_HYPHEN_REGEX,
        title="Key Prefix",
        description="Key prefix to filter.",
        examples=["sk-1735689600"],
    ),
    auth_user_id: str = Security(
        auth_deps.get_jwt_sub, scopes=[f"{_RESOURCE_NAME}:read"]
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_read),
):
    _logger: Logger = request.state.logger
    _logger.info("Getting API key list...")

    _message = "Not found any API key!"
    _api_key_list: list[dict[str, Any]] = []
    _links: dict[str, Any | None] = {
        "first": None,
        "prev": None,
        "next": None,
        "last": None,
    }
    _list_count = 0
    _total_count = 0
    try:
        _kwargs = {"user_id": auth_user_id}

        if key_prefix:
            _kwargs["key_prefix"] = key_prefix

        _api_key_orms, _total_count = await service.async_get_list(
            async_session=db_session,
            offset=skip,
            limit=(limit + 1),
            is_desc=is_desc,
            logger=_logger,
            **cast(dict[str, Any], _kwargs),
        )
        _api_key_list = UserApiKeyORM.to_dict_list(orm_objects=_api_key_orms)

        _url = request.url.remove_query_params(["skip", "limit", "is_desc"])
        if 0 < _total_count:
            _links["first"] = get_relative_url(
                _url.include_query_params(skip=0, limit=limit, is_desc=is_desc)
            )

            _last_skip = max((_total_count - 1) // limit * limit, 0)
            _links["last"] = get_relative_url(
                _url.include_query_params(skip=_last_skip, limit=limit, is_desc=is_desc)
            )

        if 0 < skip:
            _prev_skip = max(skip - limit, 0)
            _links["prev"] = get_relative_url(
                _url.include_query_params(skip=_prev_skip, limit=limit, is_desc=is_desc)
            )

        if limit < len(_api_key_list):
            _api_key_list = _api_key_list[:limit]
            _links["next"] = get_relative_url(
                _url.include_query_params(
                    skip=(skip + limit), limit=limit, is_desc=is_desc
                )
            )

        _list_count = len(_api_key_list)
        if 0 < _list_count:
            _message = "Successfully retrieved API key list."

        _logger.success(
            f"Successfully retrieved API key list count: {_list_count}/{_total_count}."
        )
    except HTTPException:
        raise
    except Exception:
        _logger.exception("Failed to get API key list!")
        raise http_errors.InternalServerError(message="Failed to get API key list!")

    _response = BaseResponse(
        request=request,
        message=_message,
        content=_api_key_list,
        links=_links,
        meta={
            "list_count": _list_count,
            "total_count": _total_count,
        },
        response_schema=ResApiKeysPM,
    )
    return _response


@router.post(
    "/",
    summary="Create API Key",
    status_code=201,
    response_model=ResCreatedApiKeyPM,
    responses={401: {}, 403: {}, 422: {}},
)
async def post_api_key(
    request: Request,
    api_key_in: ApiKeyInPM = Body(
        default_factory=ApiKeyInPM,
        title="API Key Data",
        description="API key data to create.",
    ),
    auth_user_id: str = Security(
        auth_deps.get_jwt_sub,
        scopes=[f"{_RESOURCE_NAME}:write", f"{_RESOURCE_NAME}:create"],
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Creating API key for user '{auth_user_id}' ID...")

    _api_key_dict: dict[str, Any]
    try:
        _full_api_key, _api_key_orm = await service.async_create(
            async_session=db_session,
            user_id=auth_user_id,
            api_key_in=api_key_in,
            logger=_logger,
        )
        _api_key_dict = _api_key_orm.to_dict()
        _api_key_dict["api_key"] = _full_api_key.get_secret_value()
        await db_session.commit()

        _logger.success(
            f"Successfully created API key '{_api_key_orm.id}' ID for user '{auth_user_id}' ID."
        )
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception(f"Failed to create API key for user '{auth_user_id}' ID!")
        raise http_errors.InternalServerError(message="Failed to create API key!")

    _response = BaseResponse(
        request=request,
        status_code=201,
        message="Successfully created API key.",
        content=_api_key_dict,
        response_schema=ResCreatedApiKeyPM,
    )
    return _response


@router.get(
    "/{id_}",
    summary="Get API Key",
    response_model=ResApiKeyPM,
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
async def get_api_key(
    request: Request,
    id_: str = Path(
        ...,
        min_length=8,
        max_length=64,
        pattern=ALPHANUM_HYPHEN_REGEX,
        title="API Key ID",
        description="API key ID to get.",
        examples=[
            "uak1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5"  # pragma: allowlist secret
        ],
    ),
    auth_user_id: str = Security(
        auth_deps.get_jwt_sub, scopes=[f"{_RESOURCE_NAME}:read"]
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_read),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Getting API key '{id_}' ID...")

    _api_key_dict: dict[str, Any]
    try:
        _api_key_orm = cast(
            UserApiKeyORM,
            await service.async_get(
                async_session=db_session, id_=id_, user_id=auth_user_id, logger=_logger
            ),
        )
        _api_key_dict = _api_key_orm.to_dict()

        _logger.success(f"Successfully retrieved API key '{id_}' ID.")
    except HTTPException:
        raise
    except Exception:
        _logger.exception(f"Failed to get API key '{id_}' ID!")
        raise http_errors.InternalServerError(message="Failed to get API key!")

    _response = BaseResponse(
        request=request,
        message="Successfully retrieved API key info.",
        content=_api_key_dict,
        response_schema=ResApiKeyPM,
    )
    return _response


@router.put(
    "/{id_}",
    summary="Update API Key",
    response_model=ResApiKeyPM,
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
async def put_api_key(
    request: Request,
    id_: str = Path(
        ...,
        min_length=8,
        max_length=64,
        pattern=ALPHANUM_HYPHEN_REGEX,
        title="API Key ID",
        description="API key ID to update.",
        examples=[
            "uak1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5"  # pragma: allowlist secret
        ],
    ),
    api_key_up: ApiKeyUpPM = Body(
        ..., title="API Key Data", description="API key data to update."
    ),
    auth_user_id: str = Security(
        auth_deps.get_jwt_sub,
        scopes=[f"{_RESOURCE_NAME}:write", f"{_RESOURCE_NAME}:update"],
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Updating API key '{id_}' ID...")

    _api_key_dict: dict[str, Any]
    try:
        _api_key_orm: UserApiKeyORM = await service.async_update(
            async_session=db_session,
            id_=id_,
            api_key_up=api_key_up,
            user_id=auth_user_id,
            logger=_logger,
        )
        _api_key_dict = _api_key_orm.to_dict()
        await db_session.commit()

        _logger.success(f"Successfully updated API key '{id_}' ID.")
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception(f"Failed to update API key '{id_}' ID!")
        raise http_errors.InternalServerError(message="Failed to update API key!")

    _response = BaseResponse(
        request=request,
        message="Successfully updated API key.",
        content=_api_key_dict,
        response_schema=ResApiKeyPM,
    )
    return _response


@router.delete(
    "/{id_}",
    summary="Delete API Key",
    status_code=204,
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
async def delete_api_key(
    request: Request,
    id_: str = Path(
        ...,
        min_length=8,
        max_length=64,
        pattern=ALPHANUM_HYPHEN_REGEX,
        title="API Key ID",
        description="API key ID to delete.",
        examples=[
            "uak1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5"  # pragma: allowlist secret
        ],
    ),
    auth_user_id: str = Security(
        auth_deps.get_jwt_sub,
        scopes=[f"{_RESOURCE_NAME}:write", f"{_RESOURCE_NAME}:delete"],
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Deleting API key '{id_}' ID...")

    try:
        await service.async_delete(
            async_session=db_session, id_=id_, user_id=auth_user_id, logger=_logger
        )
        await db_session.commit()

        _logger.success(f"Successfully deleted API key '{id_}' ID.")
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception(f"Failed to delete API key '{id_}' ID!")
        raise http_errors.InternalServerError(message="Failed to delete API key!")

    return


@router.patch(
    "/{id_}/status",
    summary="Update API Key Status",
    status_code=204,
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
async def patch_api_key_status(
    request: Request,
    id_: str = Path(
        ...,
        min_length=8,
        max_length=64,
        pattern=ALPHANUM_HYPHEN_REGEX,
        title="API Key ID",
        description="API key ID to update status.",
        examples=[
            "uak1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5"  # pragma: allowlist secret
        ],
    ),
    status: ApiKeyStatusUpEnum = Body(
        ...,
        title="API Key Status",
        description="API key status to update.",
        examples=[ApiKeyStatusUpEnum.ACTIVE],
    ),
    auth_user_id: str = Security(
        auth_deps.get_jwt_sub,
        scopes=[f"{_RESOURCE_NAME}:write", f"{_RESOURCE_NAME}:update"],
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Updating status of API key '{id_}' ID...")

    try:
        await service.async_update_status(
            async_session=db_session,
            id_=id_,
            status=status,  # type: ignore
            user_id=auth_user_id,
            logger=_logger,
        )
        await db_session.commit()

        _logger.success(f"Successfully updated status of API key '{id_}' ID.")
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception(f"Failed to update status of API key '{id_}' ID!")
        raise http_errors.InternalServerError(
            message="Failed to update status of API key!"
        )

    return


@router.post(
    "/{id_}/revoke",
    summary="Revoke API Key",
    status_code=204,
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
async def post_revoke_api_key(
    request: Request,
    id_: str = Path(
        ...,
        min_length=8,
        max_length=64,
        pattern=ALPHANUM_HYPHEN_REGEX,
        title="API Key ID",
        description="API key ID to revoke.",
        examples=[
            "uak1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5"  # pragma: allowlist secret
        ],
    ),
    auth_user_id: str = Security(
        auth_deps.get_jwt_sub,
        scopes=[f"{_RESOURCE_NAME}:write", f"{_RESOURCE_NAME}:revoke"],
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Revoking API key '{id_}' ID...")

    try:
        await service.async_revoke(
            async_session=db_session, id_=id_, user_id=auth_user_id, logger=_logger
        )
        await db_session.commit()
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception(f"Failed to revoke API key '{id_}' ID!")
        raise http_errors.InternalServerError(message="Failed to revoke API key!")

    return


__all__ = ["router"]
