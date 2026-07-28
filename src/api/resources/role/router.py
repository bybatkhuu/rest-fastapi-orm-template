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
from api.core.schemas import BaseResPM
from api.core.dependencies import db as db_deps
from api.core.responses import BaseResponse
from api.resources.auth import dependencies as auth_deps
from api.resources.scope.schemas import ResScopesPM
from api.resources.scope.model import ScopeORM
from api.config import config
from api.logger import Logger

from .schemas import (
    RoleExpEnum,
    RoleInPM,
    RoleUpPM,
    ResRolePM,
    ResRolesPM,
    RoleOrderByEnum,
)
from .model import RoleORM
from . import service

_RESOURCE_NAME = "roles"
router = APIRouter(prefix=f"/{_RESOURCE_NAME}", tags=["Roles"])


@router.get(
    "/",
    summary="Get Role List",
    response_model=ResRolesPM,
    responses={401: {}, 403: {}, 422: {}},
)
async def get_roles(
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
        default=False,
        title="Sort Direction",
        description="Is sort descending or ascending.",
        examples=[False, True],
    ),
    order_by: RoleOrderByEnum = Query(
        default=RoleOrderByEnum.NAME,
        title="Order By",
        description="Order by column.",
        examples=[RoleOrderByEnum.NAME],
    ),
    expands: set[RoleExpEnum] = Query(
        default={RoleExpEnum.scopes},
        title="Expands",
        description="List of related data to expand in response.",
        examples=[{RoleExpEnum.scopes}],
    ),
    name: str | None = Query(
        default=None,
        min_length=2,
        max_length=64,
        pattern=ALPHANUM_HYPHEN_REGEX,
        title="Role Name",
        description="Role name to filter.",
        examples=["user"],
    ),
    _: str = Security(auth_deps.auth_any, scopes=[f"{_RESOURCE_NAME}:read"]),
    db_session: AsyncSession = Depends(db_deps.async_get_read),
):
    _logger: Logger = request.state.logger
    _logger.info("Getting role list...")

    _message = "Not found any role!"
    _role_list: list[dict[str, Any]] = []
    _links: dict[str, Any | None] = {
        "first": None,
        "prev": None,
        "next": None,
        "last": None,
    }
    _list_count = 0
    _total_count = 0
    try:
        if RoleExpEnum.scopes not in expands:
            expands.add(RoleExpEnum.scopes)

        _kwargs = {}
        if name:
            _kwargs["name"] = name

        _role_orms, _total_count = await service.async_get_list(
            async_session=db_session,
            offset=skip,
            limit=(limit + 1),
            is_desc=is_desc,
            order_by=order_by,
            joins=expands,
            logger=_logger,
            **_kwargs,
        )
        _role_list = RoleORM.to_dict_list(
            orm_objects=_role_orms, load_relations=expands
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

        if limit < len(_role_list):
            _role_list = _role_list[:limit]
            _query_params["skip"] = skip + limit
            _links["next"] = get_relative_url(
                _url.include_query_params(**_query_params)
            )

        _list_count = len(_role_list)
        if 0 < _list_count:
            _message = "Successfully retrieved role list."

        _logger.success(
            f"Successfully retrieved role list count: {_list_count}/{_total_count}."
        )
    except HTTPException:
        raise
    except Exception:
        _logger.exception("Failed to get role list!")
        raise http_errors.InternalServerError(message="Failed to get role list!")

    _response = BaseResponse(
        request=request,
        message=_message,
        content=_role_list,
        links=_links,
        meta={
            "list_count": _list_count,
            "total_count": _total_count,
        },
        response_schema=ResRolesPM,
    )
    return _response


@router.post(
    "/",
    summary="Create Role",
    status_code=201,
    response_model=ResRolePM,
    responses={401: {}, 403: {}, 422: {}},
)
async def post_role(
    request: Request,
    role_in: RoleInPM = Body(
        ...,
        title="Role Data",
        description="Role data to create.",
    ),
    _: str = Security(
        auth_deps.auth_any,
        scopes=[f"{_RESOURCE_NAME}:write", f"{_RESOURCE_NAME}:create"],
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Creating role '{role_in.name}' name...")

    _role_dict: dict[str, Any]
    try:
        _role_orm: RoleORM = await service.async_create(
            async_session=db_session, role_in=role_in, logger=_logger
        )
        _role_dict = _role_orm.to_dict(load_relations=["scopes"])
        await db_session.commit()

        _logger.success(
            f"Successfully created role '{role_in.name}' name with '{_role_orm.id}' ID."
        )
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception(f"Failed to create role '{role_in.name}' name!")
        raise http_errors.InternalServerError(message="Failed to create role!")

    _response = BaseResponse(
        request=request,
        status_code=201,
        message="Successfully created role.",
        content=_role_dict,
        response_schema=ResRolePM,
    )
    return _response


@router.get(
    "/{name}",
    summary="Get Role",
    response_model=ResRolePM,
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
async def get_role(
    request: Request,
    name: str = Path(
        ...,
        min_length=2,
        max_length=64,
        pattern=ALPHANUM_HYPHEN_REGEX,
        title="Role Name",
        description="Role name to get.",
        examples=["user"],
    ),
    expands: set[RoleExpEnum] | None = Query(
        default=None,
        title="Expands",
        description="List of related data to expand in response.",
    ),
    _: str = Security(auth_deps.auth_any, scopes=[f"{_RESOURCE_NAME}:read"]),
    db_session: AsyncSession = Depends(db_deps.async_get_read),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Getting role '{name}' name...")

    _role_dict: dict[str, Any]
    try:
        if not expands:
            expands = set()
        expands.add(RoleExpEnum.scopes)

        _role_orm = cast(
            RoleORM,
            await service.async_get(
                async_session=db_session, name=name, joins=expands, logger=_logger
            ),
        )
        _role_dict = _role_orm.to_dict(load_relations=expands)

        _logger.success(f"Successfully retrieved role '{name}' name.")
    except HTTPException:
        raise
    except Exception:
        _logger.exception(f"Failed to get role '{name}' name!")
        raise http_errors.InternalServerError(message="Failed to get role!")

    _response = BaseResponse(
        request=request,
        message="Successfully retrieved role info.",
        content=_role_dict,
        response_schema=ResRolePM,
    )
    return _response


@router.put(
    "/{name}",
    summary="Update Role",
    response_model=ResRolePM,
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
async def put_role(
    request: Request,
    name: str = Path(
        ...,
        min_length=2,
        max_length=64,
        pattern=ALPHANUM_HYPHEN_REGEX,
        title="Role Name",
        description="Role name to update.",
        examples=["user"],
    ),
    role_up: RoleUpPM = Body(
        ...,
        title="Role Data",
        description="Role data to update.",
    ),
    _: str = Security(
        auth_deps.auth_any,
        scopes=[f"{_RESOURCE_NAME}:write", f"{_RESOURCE_NAME}:update"],
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Updating role '{name}' name...")

    _role_dict: dict[str, Any]
    try:
        _role_orm: RoleORM = await service.async_update(
            async_session=db_session, name=name, role_up=role_up, logger=_logger
        )
        _role_dict = _role_orm.to_dict(load_relations=["scopes"])
        await db_session.commit()

        _logger.success(f"Successfully updated role '{name}' name.")
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception(f"Failed to update role '{name}' name!")
        raise http_errors.InternalServerError(message="Failed to update role!")

    _response = BaseResponse(
        request=request,
        message="Successfully updated role.",
        content=_role_dict,
        response_schema=ResRolePM,
    )
    return _response


@router.delete(
    "/{name}",
    summary="Delete Role",
    status_code=204,
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
async def delete_role(
    request: Request,
    name: str = Path(
        ...,
        min_length=2,
        max_length=64,
        pattern=ALPHANUM_HYPHEN_REGEX,
        title="Role Name",
        description="Role name to delete.",
        examples=["user"],
    ),
    _: str = Security(
        auth_deps.auth_any,
        scopes=[f"{_RESOURCE_NAME}:write", f"{_RESOURCE_NAME}:delete"],
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Deleting role '{name}' name...")

    try:
        await service.async_delete(async_session=db_session, name=name, logger=_logger)
        await db_session.commit()

        _logger.success(f"Successfully deleted role '{name}' name.")
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception(f"Failed to delete role '{name}' name!")
        raise http_errors.InternalServerError(message="Failed to delete role!")

    return


@router.patch(
    "/{name}/protected",
    summary="Change Role Protection",
    status_code=204,
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
async def patch_role_protected(
    request: Request,
    name: str = Path(
        ...,
        min_length=2,
        max_length=64,
        pattern=ALPHANUM_HYPHEN_REGEX,
        title="Role Name",
        description="Role name to update protected flag.",
        examples=["user"],
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
    _logger.info(f"Updating protected flag of role '{name}' name...")

    try:
        await service.async_update_protected(
            async_session=db_session, name=name, protected=protected, logger=_logger
        )
        await db_session.commit()

        _logger.success(f"Successfully updated protected flag of role '{name}' name.")
    except Exception as err:

        if isinstance(err, HTTPException):
            raise

        _logger.exception(f"Failed to update protected flag of role '{name}' name!")
        raise http_errors.InternalServerError(
            message="Failed to update protected flag of role!"
        )

    return


@router.get(
    "/{name}/scopes",
    summary="Get Role Scopes",
    response_model=ResScopesPM,
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
async def get_role_scopes(
    request: Request,
    name: str = Path(
        ...,
        min_length=2,
        max_length=64,
        pattern=ALPHANUM_HYPHEN_REGEX,
        title="Role Name",
        description="Role name to get scopes from.",
        examples=["user"],
    ),
    simple: bool = Query(
        default=True,
        title="Simple",
        description="Whether to return a simple list of scopes values instead of full scope objects.",
        examples=[True, False],
    ),
    _: str = Security(auth_deps.auth_any, scopes=[f"{_RESOURCE_NAME}:read"]),
    db_session: AsyncSession = Depends(db_deps.async_get_read),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Getting scopes of role '{name}' name...")

    _scope_list: list[dict[str, Any]] | list[str] = []
    _list_count = 0
    try:
        _scope_orms = await service.async_get_scopes(
            async_session=db_session, name=name, logger=_logger
        )

        if simple:
            _scope_list = [scope.value for scope in _scope_orms]
        else:
            _scope_list = ScopeORM.to_dict_list(orm_objects=_scope_orms)

        _list_count = len(_scope_list)
        _logger.success(
            f"Successfully retrieved scopes of role '{name}' name: {_list_count}."
        )
    except HTTPException:
        raise
    except Exception:
        _logger.exception(f"Failed to get scopes of role '{name}' name!")
        raise http_errors.InternalServerError(message="Failed to get role scopes!")

    _message = "Not found any scope for that role!"
    if 0 < _list_count:
        _message = "Successfully retrieved role scopes."

    _response_schema = BaseResPM if simple else ResScopesPM
    _response = BaseResponse(
        request=request,
        message=_message,
        content=_scope_list,
        meta={"list_count": _list_count},
        response_schema=_response_schema,
    )
    return _response


__all__ = ["router"]
