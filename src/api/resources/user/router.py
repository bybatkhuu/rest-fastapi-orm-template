from typing import Any, cast

from pydantic import SecretStr, EmailStr
from fastapi import (
    APIRouter,
    Request,
    HTTPException,
    Depends,
    Security,
    Path,
    Query,
    Body,
)
from sqlalchemy.ext.asyncio import AsyncSession

from potato_util.constants import ALPHANUM_HYPHEN_REGEX, ALPHANUM_EXTEND_REGEX
from potato_util.http.fastapi import get_relative_url

from api.core.exceptions import http as http_errors
from api.core.dependencies import db as db_deps
from api.core.schemas import BaseResPM
from api.core.responses import BaseResponse
from api.resources.auth import dependencies as auth_deps
from api.config import config
from api.logger import Logger

from .schemas import (
    UserExpEnum,
    UserInPM,
    UserUpPM,
    ResUserPM,
    ResUsersPM,
    UserStatusUpEnum,
    UserOrderByEnum,
)
from .model import UserORM
from . import service

_RESOURCE_NAME = "users"
router = APIRouter(prefix=f"/{_RESOURCE_NAME}", tags=["Users"])


@router.get(
    "/",
    summary="Get User List",
    response_model=ResUsersPM,
    responses={401: {}, 403: {}, 422: {}},
)
async def get_users(
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
        examples=[True, False],
    ),
    order_by: UserOrderByEnum | None = Query(
        default=None, title="Order By", description="Order by column."
    ),
    expands: set[UserExpEnum] = Query(
        default={UserExpEnum.roles},
        title="Expands",
        description="List of related data to expand in response.",
        examples=[{UserExpEnum.roles}],
    ),
    email: EmailStr | None = Query(
        default=None,
        title="Email",
        description="Email address to filter.",
        examples=["user@example.com"],
    ),
    nickname: str | None = Query(
        default=None,
        min_length=1,
        max_length=64,
        pattern=ALPHANUM_EXTEND_REGEX,
        title="Nickname",
        description="Nickname to filter.",
        examples=["User 1"],
    ),
    _: str = Security(auth_deps.auth_any, scopes=[f"{_RESOURCE_NAME}:read"]),
    db_session: AsyncSession = Depends(db_deps.async_get_read),
):
    _logger: Logger = request.state.logger
    _logger.info("Getting user list...")

    _message = "Not found any user!"
    _user_list: list[dict[str, Any]] = []
    _links: dict[str, Any | None] = {
        "first": None,
        "prev": None,
        "next": None,
        "last": None,
    }
    _list_count = 0
    _total_count = 0
    try:
        if UserExpEnum.roles not in expands:
            expands.add(UserExpEnum.roles)

        _kwargs = {}
        if email:
            _kwargs["email"] = email

        if nickname:
            _kwargs["nickname"] = nickname

        _user_orms, _total_count = await service.async_get_list(
            async_session=db_session,
            offset=skip,
            limit=(limit + 1),
            is_desc=is_desc,
            order_by=order_by,
            joins=expands,
            logger=_logger,
            **_kwargs,
        )
        _user_list = UserORM.to_dict_list(
            orm_objects=_user_orms, load_relations=expands
        )

        _query_params = {"skip": skip, "limit": limit, "is_desc": is_desc}
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

        if limit < len(_user_list):
            _user_list = _user_list[:limit]
            _query_params["skip"] = skip + limit
            _links["next"] = get_relative_url(
                _url.include_query_params(**_query_params)
            )

        _list_count = len(_user_list)
        if 0 < _list_count:
            _message = "Successfully retrieved user list."

        _logger.success(
            f"Successfully retrieved user list count: {_list_count}/{_total_count}."
        )
    except HTTPException:
        raise
    except Exception:
        _logger.exception("Failed to get user list!")
        raise http_errors.InternalServerError(message="Failed to get user list!")

    _response = BaseResponse(
        request=request,
        message=_message,
        content=_user_list,
        links=_links,
        meta={
            "list_count": _list_count,
            "total_count": _total_count,
        },
        response_schema=ResUsersPM,
    )
    return _response


@router.post(
    "/",
    summary="Create User",
    status_code=201,
    response_model=ResUserPM,
    responses={401: {}, 403: {}, 409: {}, 422: {}},
)
async def post_user(
    request: Request,
    user_in: UserInPM = Body(
        ...,
        title="User Data",
        description="User data to create.",
    ),
    _: str = Security(
        auth_deps.auth_any,
        scopes=[f"{_RESOURCE_NAME}:write", f"{_RESOURCE_NAME}:create"],
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Creating user with '{user_in.email}' email...")

    _user_dict: dict[str, Any]
    try:
        _user_orm: UserORM = await service.async_create(
            async_session=db_session, user_in=user_in, logger=_logger
        )
        _user_dict = _user_orm.to_dict(load_relations=["roles"])
        await db_session.commit()

        _logger.success(
            f"Successfully created user with '{user_in.email}' email and '{_user_orm.id}' ID."
        )
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception(f"Failed to create user with '{user_in.email}' email!")
        raise http_errors.InternalServerError(message="Failed to create user!")

    _response = BaseResponse(
        request=request,
        status_code=201,
        message="Successfully created user.",
        content=_user_dict,
        response_schema=ResUserPM,
    )
    return _response


@router.get(
    "/{id_}",
    summary="Get User",
    response_model=ResUserPM,
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
async def get_user(
    request: Request,
    id_: str = Path(
        ...,
        min_length=8,
        max_length=64,
        pattern=ALPHANUM_HYPHEN_REGEX,
        title="User ID",
        description="User ID to get.",
        examples=[
            "use1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5"  # pragma: allowlist secret
        ],
    ),
    expands: set[UserExpEnum] | None = Query(
        default=None,
        title="Expands",
        description="List of related data to expand in response.",
    ),
    _: str = Security(auth_deps.auth_any, scopes=[f"{_RESOURCE_NAME}:read"]),
    db_session: AsyncSession = Depends(db_deps.async_get_read),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Getting user '{id_}' ID...")

    _user_dict: dict[str, Any]
    try:
        if not expands:
            expands = set()
        expands.add(UserExpEnum.roles)

        _user_orm = cast(
            UserORM,
            await service.async_get(
                async_session=db_session, id_=id_, joins=expands, logger=_logger
            ),
        )
        _user_dict = _user_orm.to_dict(load_relations=expands)

        _logger.success(f"Successfully retrieved user '{id_}' ID.")
    except HTTPException:
        raise
    except Exception:
        _logger.exception(f"Failed to get user '{id_}' ID!")
        raise http_errors.InternalServerError(message="Failed to get user!")

    _response = BaseResponse(
        request=request,
        message="Successfully retrieved user info.",
        content=_user_dict,
        response_schema=ResUserPM,
    )
    return _response


@router.put(
    "/{id_}",
    summary="Update User",
    response_model=ResUserPM,
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
async def put_user(
    request: Request,
    id_: str = Path(
        ...,
        min_length=8,
        max_length=64,
        pattern=ALPHANUM_HYPHEN_REGEX,
        title="User ID",
        description="User ID to update.",
        examples=[
            "use1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5"  # pragma: allowlist secret
        ],
    ),
    user_up: UserUpPM = Body(
        ...,
        title="User Data",
        description="User data to update.",
    ),
    auth_user_id: str = Security(
        auth_deps.auth_any,
        scopes=[f"{_RESOURCE_NAME}:write", f"{_RESOURCE_NAME}:update"],
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Updating user '{id_}' ID...")

    if auth_user_id == id_:
        raise http_errors.UnprocessableEntityError(
            message="You can not update your own info, use '/users/me' endpoint instead!"
        )

    _user_dict: dict[str, Any]
    try:
        _user_orm: UserORM = await service.async_update(
            async_session=db_session, id_=id_, user_up=user_up, logger=_logger
        )
        _user_dict = _user_orm.to_dict(load_relations=["roles"])
        await db_session.commit()

        _logger.success(f"Successfully updated user '{id_}' ID.")
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception(f"Failed to update user '{id_}' ID!")
        raise http_errors.InternalServerError(message="Failed to update user!")

    _response = BaseResponse(
        request=request,
        message="Successfully updated user.",
        content=_user_dict,
        response_schema=ResUserPM,
    )
    return _response


@router.delete(
    "/{id_}",
    summary="Delete User",
    status_code=204,
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
async def delete_user(
    request: Request,
    id_: str = Path(
        ...,
        min_length=8,
        max_length=64,
        pattern=ALPHANUM_HYPHEN_REGEX,
        title="User ID",
        description="User ID to delete.",
        examples=[
            "use1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5"  # pragma: allowlist secret
        ],
    ),
    auth_user_id: str = Security(
        auth_deps.auth_any,
        scopes=[f"{_RESOURCE_NAME}:write", f"{_RESOURCE_NAME}:delete"],
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Deleting user '{id_}' ID...")

    if auth_user_id == id_:
        raise http_errors.UnprocessableEntityError(
            message="You can not delete your own account, use [DELETE] '/users/me' endpoint instead!"
        )

    try:
        await service.async_delete(async_session=db_session, id_=id_, logger=_logger)
        await db_session.commit()

        _logger.success(f"Successfully deleted user '{id_}' ID.")
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception(f"Failed to delete user '{id_}' ID!")
        raise http_errors.InternalServerError(message="Failed to delete user!")

    return


@router.patch(
    "/{id_}/status",
    summary="Update User Status",
    status_code=204,
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
async def patch_user_status(
    request: Request,
    id_: str = Path(
        ...,
        min_length=8,
        max_length=64,
        pattern=ALPHANUM_HYPHEN_REGEX,
        title="User ID",
        description="User ID to update status.",
        examples=[
            "use1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5"  # pragma: allowlist secret
        ],
    ),
    status: UserStatusUpEnum = Body(
        ...,
        title="User Status",
        description="User status to update.",
        examples=[UserStatusUpEnum.ACTIVE],
    ),
    auth_user_id: str = Security(
        auth_deps.auth_any,
        scopes=[f"{_RESOURCE_NAME}:write", f"{_RESOURCE_NAME}:update"],
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Updating status of user '{id_}' ID...")

    if (auth_user_id == id_) and (status == UserStatusUpEnum.DISABLED):
        raise http_errors.UnprocessableEntityError(
            message="You can not disable your own account!"
        )

    try:
        await service.async_update_status(
            async_session=db_session,
            id_=id_,
            status=status,  # type: ignore
            logger=_logger,
        )
        await db_session.commit()

        _logger.success(f"Successfully updated status of user '{id_}' ID.")
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception(f"Failed to update status of user '{id_}' ID!")
        raise http_errors.InternalServerError(
            message="Failed to update status of user!"
        )

    return


@router.patch(
    "/{id_}/protected",
    summary="Change User Protection",
    status_code=204,
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
async def patch_user_protected(
    request: Request,
    id_: str = Path(
        ...,
        min_length=8,
        max_length=64,
        pattern=ALPHANUM_HYPHEN_REGEX,
        title="User ID",
        description="User ID to update protection flag.",
        examples=[
            "use1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5"  # pragma: allowlist secret
        ],
    ),
    protected: bool = Body(
        ...,
        title="Protected Flag",
        description="Protected flag to update.",
        examples=[True, False],
    ),
    auth_user_id: str = Security(
        auth_deps.auth_any,
        scopes=[f"{_RESOURCE_NAME}:protection"],
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Updating protected flag of user '{id_}' ID...")

    if auth_user_id == id_:
        raise http_errors.UnprocessableEntityError(
            message="You can not change your own protection flag, only other admin user(s) can change it!"
        )

    try:
        await service.async_update_protected(
            async_session=db_session, id_=id_, protected=protected, logger=_logger
        )
        await db_session.commit()

        _logger.success(f"Successfully updated protected flag of user '{id_}' ID.")
    except Exception as err:

        if isinstance(err, HTTPException):
            raise

        _logger.exception(f"Failed to update protected flag of user '{id_}' ID!")
        raise http_errors.InternalServerError(
            message="Failed to update protected flag of user!"
        )

    return


@router.post(
    "/{id_}/password",
    summary="Update User Password",
    response_model=BaseResPM,
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
async def post_user_password(
    request: Request,
    id_: str = Path(
        ...,
        min_length=8,
        max_length=64,
        pattern=ALPHANUM_HYPHEN_REGEX,
        title="User ID",
        description="User ID to update password.",
        examples=[
            "use1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5"  # pragma: allowlist secret
        ],
    ),
    password: SecretStr = Body(
        ...,
        min_length=config.api.security.password.min_length,
        max_length=config.api.security.password.max_length,
        title="Password",
        description="New password for the user.",
        embed=True,
        examples=["your_password"],  # pragma: allowlist secret
    ),
    logout_all: bool = Body(
        default=False,
        title="Logout All",
        description="Logout from all logged in sessions of the user.",
        examples=[False],
    ),
    auth_user_id: str = Security(
        auth_deps.auth_any,
        scopes=[f"{_RESOURCE_NAME}:password"],
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Updating password of user '{id_}' ID...")

    if auth_user_id == id_:
        raise http_errors.UnprocessableEntityError(
            message="You can not update your own password, use [POST] '/users/me/password' endpoint instead!"
        )

    _user_dict: dict[str, Any] = {"id": id_}
    try:
        await service.async_update_password(
            async_session=db_session,
            id_=id_,
            password=password,
            logout_all=logout_all,
            logger=_logger,
        )
        await db_session.commit()

        _logger.success(f"Successfully updated password of user '{id_}' ID.")
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception(f"Failed to update password of user '{id_}' ID!")
        raise http_errors.InternalServerError(message="Failed to update user password!")

    _response = BaseResponse(
        request=request,
        message="Successfully updated user password.",
        content=_user_dict,
    )
    if logout_all:
        _response.delete_cookie(key="access_token")
        _response.delete_cookie(key="refresh_token")

    return


__all__ = ["router"]
