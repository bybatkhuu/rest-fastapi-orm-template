from typing import Annotated, Any, cast

from pydantic import StringConstraints
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

from potato_util.constants import ALPHANUM_SCOPE_REGEX
from potato_util.http.fastapi import get_relative_url

from api.core.exceptions import http as http_errors
from api.core.dependencies import db as db_deps
from api.core.responses import BaseResponse
from api.resources.auth import dependencies as auth_deps
from api.config import config
from api.logger import Logger

from .schemas import (
    ScopeExpEnum,
    ScopeOrderByEnum,
    ScopeInPM,
    ScopeUpPM,
    ResScopePM,
    ResScopesPM,
)
from .model import ScopeORM
from . import service

_RESOURCE_NAME = "scopes"
router = APIRouter(prefix=f"/{_RESOURCE_NAME}", tags=["Scopes"])


@router.get(
    "/",
    summary="Get Scope List",
    response_model=ResScopesPM,
    responses={401: {}, 403: {}, 422: {}},
)
async def get_scopes(
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
        examples=[config.db.select_limit],
    ),
    is_desc: bool = Query(
        default=False,
        title="Sort Direction",
        description="Is sort descending or ascending.",
        examples=[False, True],
    ),
    order_by: ScopeOrderByEnum = Query(
        default=ScopeOrderByEnum.VALUE,
        title="Order By",
        description="Order by column.",
        examples=[ScopeOrderByEnum.VALUE],
    ),
    expands: set[ScopeExpEnum] | None = Query(
        default=None,
        title="Expands",
        description="List of related data to expand in response.",
    ),
    value: str | None = Query(
        default=None,
        min_length=2,
        max_length=128,
        pattern=ALPHANUM_SCOPE_REGEX,
        title="Scope Value",
        description="Scope value to filter.",
        examples=["me:read"],
    ),
    _: str = Security(auth_deps.auth_any, scopes=[f"{_RESOURCE_NAME}:read"]),
    db_session: AsyncSession = Depends(db_deps.async_get_read),
):
    _logger: Logger = request.state.logger
    _logger.info("Getting scope list...")

    _message = "Not found any scope!"
    _scope_list: list[dict[str, Any]] = []
    _links: dict[str, Any | None] = {
        "first": None,
        "prev": None,
        "next": None,
        "last": None,
    }
    _list_count = 0
    _total_count = 0
    try:
        _kwargs = {}
        if value:
            _kwargs["value"] = value

        _scope_orms, _total_count = await service.async_get_list(
            async_session=db_session,
            offset=skip,
            limit=(limit + 1),
            is_desc=is_desc,
            order_by=order_by,
            joins=expands,
            logger=_logger,
            **_kwargs,
        )
        _scope_list = ScopeORM.to_dict_list(
            orm_objects=_scope_orms, load_relations=expands
        )

        _query_params = {
            "skip": skip,
            "limit": limit,
            "is_desc": is_desc,
            "order_by": order_by.value,
        }
        _url = request.url.remove_query_params(list[str](_query_params.keys()))

        if 0 < _total_count:
            _query_params["skip"] = 0
            _links["first"] = get_relative_url(
                _url.include_query_params(**_query_params)
            )

            _query_params["skip"] = max((_total_count - 1) // limit * limit, 0)
            _links["last"] = get_relative_url(
                _url.include_query_params(**_query_params)
            )

        if 0 < skip:
            _query_params["skip"] = max(skip - limit, 0)
            _links["prev"] = get_relative_url(
                _url.include_query_params(**_query_params)
            )

        if limit < len(_scope_list):
            _scope_list = _scope_list[:limit]
            _query_params["skip"] = skip + limit
            _links["next"] = get_relative_url(
                _url.include_query_params(**_query_params)
            )

        _list_count = len(_scope_list)
        if 0 < _list_count:
            _message = "Successfully retrieved scope list."

        _logger.success(
            f"Successfully retrieved scope list count: {_list_count}/{_total_count}."
        )
    except HTTPException:
        raise
    except Exception:
        _logger.exception("Failed to get scope list!")
        raise http_errors.InternalServerError(message="Failed to get scope list!")

    _response = BaseResponse(
        request=request,
        message=_message,
        content=_scope_list,
        links=_links,
        meta={
            "list_count": _list_count,
            "total_count": _total_count,
        },
        response_schema=ResScopesPM,
    )
    return _response


@router.post(
    "/",
    summary="Create Scope",
    status_code=201,
    response_model=ResScopePM,
    responses={401: {}, 403: {}, 422: {}},
)
async def post_scope(
    request: Request,
    scope_in: ScopeInPM = Body(
        ...,
        title="Scope Data",
        description="Scope data to create.",
    ),
    _: str = Security(
        auth_deps.auth_any,
        scopes=[f"{_RESOURCE_NAME}:write", f"{_RESOURCE_NAME}:create"],
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Creating scope '{scope_in.value}' value...")

    _scope_dict: dict[str, Any]
    try:
        _scope_orm: ScopeORM = await service.async_create(
            async_session=db_session, scope_in=scope_in, logger=_logger
        )
        _scope_dict = _scope_orm.to_dict()
        await db_session.commit()

        _logger.success(
            f"Successfully created scope '{scope_in.value}' value and '{_scope_orm.id}' ID."
        )
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception(f"Failed to create scope '{scope_in.value}' value!")
        raise http_errors.InternalServerError(message="Failed to create scope!")

    _response = BaseResponse(
        request=request,
        status_code=201,
        message="Successfully created scope.",
        content=_scope_dict,
        response_schema=ResScopePM,
    )
    return _response


@router.delete(
    "/",
    summary="Bulk Delete Scopes",
    status_code=204,
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
async def delete_scopes(
    request: Request,
    values: set[
        Annotated[
            str,
            StringConstraints(
                min_length=2, max_length=128, pattern=ALPHANUM_SCOPE_REGEX
            ),
        ]
    ] = Body(
        ...,
        min_length=1,
        title="Scope Values",
        description="Set of scope values to delete.",
        examples=[{"me:read", "me:write"}],
    ),
    _: str = Security(
        auth_deps.auth_any,
        scopes=[f"{_RESOURCE_NAME}:write", f"{_RESOURCE_NAME}:delete"],
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Deleting {len(values)} scope(s) by values...")

    try:
        await service.async_bulk_delete(
            async_session=db_session, values=values, logger=_logger
        )
        await db_session.commit()

        _logger.success(f"Successfully deleted {len(values)} scope(s) by values.")
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception("Failed to delete scopes by values!")
        raise http_errors.InternalServerError(
            message="Failed to delete scopes by values!"
        )

    return


@router.patch(
    "/protected",
    summary="Bulk Update Scope Protection",
    status_code=204,
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
async def patch_scopes_protected(
    request: Request,
    values: set[
        Annotated[
            str,
            StringConstraints(
                min_length=2, max_length=128, pattern=ALPHANUM_SCOPE_REGEX
            ),
        ]
    ] = Body(
        ...,
        min_length=1,
        title="Scope Values",
        description="Set of scope values to update protected flag.",
        examples=[{"me:read", "me:write"}],
    ),
    protected: bool = Body(
        ...,
        title="Protected Flag",
        description="Protected flag to update.",
        examples=[True, False],
    ),
    _: str = Security(
        auth_deps.auth_any,
        scopes=[f"{_RESOURCE_NAME}:protection"],
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Updating protected flag for {len(values)} scope(s) by values...")

    try:
        await service.async_bulk_update_protected(
            async_session=db_session, values=values, protected=protected, logger=_logger
        )
        await db_session.commit()

        _logger.success(
            f"Successfully updated protected flag for {len(values)} scope(s) by values."
        )
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception(
            f"Failed to update protected flag for {len(values)} scope(s) by values!"
        )
        raise http_errors.InternalServerError(
            message="Failed to update protected flag for scope(s) by values!"
        )

    return


@router.get(
    "/{value}",
    summary="Get Scope",
    response_model=ResScopePM,
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
async def get_scope(
    request: Request,
    value: str = Path(
        ...,
        min_length=2,
        max_length=128,
        pattern=ALPHANUM_SCOPE_REGEX,
        title="Scope Value",
        description="Scope value to get.",
        examples=["me:read"],
    ),
    expands: set[ScopeExpEnum] | None = Query(
        default=None,
        title="Expands",
        description="List of related data to expand in response.",
    ),
    _: str = Security(auth_deps.auth_any, scopes=[f"{_RESOURCE_NAME}:read"]),
    db_session: AsyncSession = Depends(db_deps.async_get_read),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Getting scope '{value}' value...")

    _scope_dict: dict[str, Any]
    try:
        _scope_orm = cast(
            ScopeORM,
            await service.async_get(
                async_session=db_session, value=value, joins=expands, logger=_logger
            ),
        )
        _scope_dict = _scope_orm.to_dict(load_relations=expands)

        _logger.success(f"Successfully retrieved scope '{value}' value.")
    except HTTPException:
        raise
    except Exception:
        _logger.exception(f"Failed to get scope '{value}' value!")
        raise http_errors.InternalServerError(message="Failed to get scope!")

    _response = BaseResponse(
        request=request,
        message="Successfully retrieved scope info.",
        content=_scope_dict,
        response_schema=ResScopePM,
    )
    return _response


@router.put(
    "/{value}",
    summary="Update Scope",
    response_model=ResScopePM,
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
async def put_scope(
    request: Request,
    value: str = Path(
        ...,
        min_length=2,
        max_length=128,
        pattern=ALPHANUM_SCOPE_REGEX,
        title="Scope Value",
        description="Scope value to update.",
        examples=["me:read"],
    ),
    scope_up: ScopeUpPM = Body(
        ...,
        title="Scope Data",
        description="Scope data to update.",
    ),
    _: str = Security(
        auth_deps.auth_any,
        scopes=[f"{_RESOURCE_NAME}:write", f"{_RESOURCE_NAME}:update"],
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Updating scope '{value}' value...")

    _scope_dict: dict[str, Any]
    try:
        _scope_orm: ScopeORM = await service.async_update(
            async_session=db_session, value=value, scope_up=scope_up, logger=_logger
        )
        _scope_dict = _scope_orm.to_dict()
        await db_session.commit()

        _logger.success(f"Successfully updated scope '{value}' value.")
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception(f"Failed to update scope '{value}' value!")
        raise http_errors.InternalServerError(message="Failed to update scope!")

    _response = BaseResponse(
        request=request,
        message="Successfully updated scope.",
        content=_scope_dict,
        response_schema=ResScopePM,
    )
    return _response


@router.delete(
    "/{value}",
    summary="Delete Scope",
    status_code=204,
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
async def delete_scope(
    request: Request,
    value: str = Path(
        ...,
        min_length=2,
        max_length=128,
        pattern=ALPHANUM_SCOPE_REGEX,
        title="Scope Value",
        description="Scope value to delete.",
        examples=["me:read"],
    ),
    _: str = Security(
        auth_deps.auth_any,
        scopes=[f"{_RESOURCE_NAME}:write", f"{_RESOURCE_NAME}:delete"],
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Deleting scope '{value}' value...")

    try:
        await service.async_delete(
            async_session=db_session, value=value, logger=_logger
        )
        await db_session.commit()

        _logger.success(f"Successfully deleted scope '{value}' value.")
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception(f"Failed to delete scope '{value}' value!")
        raise http_errors.InternalServerError(message="Failed to delete scope!")

    return


@router.patch(
    "/{value}/protected",
    summary="Change Scope Protection",
    status_code=204,
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
async def patch_scope_protected(
    request: Request,
    value: str = Path(
        ...,
        min_length=2,
        max_length=128,
        pattern=ALPHANUM_SCOPE_REGEX,
        title="Scope Value",
        description="Scope value to update protected flag.",
        examples=["me:read"],
    ),
    protected: bool = Body(
        ...,
        title="Protected Flag",
        description="Protected flag to update.",
        examples=[True, False],
    ),
    _: str = Security(
        auth_deps.auth_any,
        scopes=[f"{_RESOURCE_NAME}:protection"],
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Updating protected flag of scope '{value}' value...")

    try:
        await service.async_update_protected(
            async_session=db_session, value=value, protected=protected, logger=_logger
        )
        await db_session.commit()

        _logger.success(
            f"Successfully updated protected flag of scope '{value}' value."
        )
    except Exception as err:

        if isinstance(err, HTTPException):
            raise

        _logger.exception(f"Failed to update protected flag of scope '{value}' value!")
        raise http_errors.InternalServerError(
            message="Failed to update protected flag of scope!"
        )

    return


__all__ = ["router"]
