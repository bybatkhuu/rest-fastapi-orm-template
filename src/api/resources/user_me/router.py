from typing import Any, cast

from pydantic import SecretStr
from fastapi import APIRouter, Request, HTTPException, Depends, Security, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.exceptions import http as http_errors
from api.core.dependencies import db as db_deps
from api.core.schemas import BaseResPM
from api.core.responses import BaseResponse
from api.resources.auth import dependencies as auth_deps
from api.resources.user.schemas import UserExpEnum, ResUserPM
from api.resources.user.model import UserORM
from api.config import config
from api.logger import Logger

from .schemas import UserMeUpPM, UserMeChangePasswordPM
from . import service

_RESOURCE_NAME = "me"
router = APIRouter(prefix="/users/me", tags=["User Me"])


@router.get(
    "/",
    summary="Get My Info",
    response_model=ResUserPM,
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
async def get_me(
    request: Request,
    expands: set[UserExpEnum] | None = Query(
        default=None,
        title="Expands",
        description="List of related data to expand in response.",
    ),
    auth_user_id: str = Security(auth_deps.auth_any, scopes=[f"{_RESOURCE_NAME}:read"]),
    db_session: AsyncSession = Depends(db_deps.async_get_read),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Getting user ('{auth_user_id}' ID) info...")

    _user_dict: dict[str, Any]
    try:
        if not expands:
            expands = set()
        expands.add(UserExpEnum.roles)

        _user_orm = cast(
            UserORM,
            await service.async_get_me(
                async_session=db_session,
                id_=auth_user_id,
                joins=expands,
                logger=_logger,
            ),
        )
        _user_dict = _user_orm.to_dict(load_relations=expands)

        _logger.success(f"Successfully retrieved user ('{auth_user_id}' ID) info.")
    except HTTPException:
        raise
    except Exception:
        _logger.exception(f"Failed to get user ('{auth_user_id}' ID) info!")
        raise http_errors.InternalServerError(
            message="Failed to get your account info!"
        )

    _response = BaseResponse(
        request=request,
        message="Successfully retrieved your account info.",
        content=_user_dict,
        response_schema=ResUserPM,
    )
    return _response


@router.put(
    "/",
    summary="Update My Info",
    response_model=ResUserPM,
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
async def post_me(
    request: Request,
    user_up: UserMeUpPM = Body(
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
    _logger.info(f"Updating user ('{auth_user_id}' ID) info...")

    _user_dict: dict[str, Any]
    try:
        _user_orm: UserORM = await service.async_update_me(
            async_session=db_session, id_=auth_user_id, user_up=user_up, logger=_logger
        )
        _user_dict = _user_orm.to_dict(load_relations=["roles"])
        await db_session.commit()

        _logger.success(f"Successfully updated user ('{auth_user_id}' ID) info.")
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception(f"Failed to update user ('{auth_user_id}' ID) info!")
        raise http_errors.InternalServerError(
            message="Failed to update your account info!"
        )

    _response = BaseResponse(
        request=request,
        message="Successfully updated your account info.",
        content=_user_dict,
        response_schema=ResUserPM,
    )
    return _response


@router.post(
    "/password",
    summary="Change My Password",
    response_model=BaseResPM,
    responses={401: {}, 403: {}, 422: {}},
)
async def post_change_password(
    request: Request,
    user_change_password: UserMeChangePasswordPM = Body(
        ...,
        title="Change Password Data",
        description="Password data to change my account password.",
    ),
    auth_user_id: str = Security(
        auth_deps.get_jwt_sub, scopes=[f"{_RESOURCE_NAME}:password"]
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info(
        f"Changing user ('{auth_user_id}' ID) current password with new password..."
    )

    _user_dict: dict[str, Any] = {"id": auth_user_id}
    try:
        await service.async_change_my_password(
            async_session=db_session,
            id_=auth_user_id,
            user_change_password=user_change_password,
            logger=_logger,
        )
        await db_session.commit()

        _logger.success(
            f"Successfully changed user ('{auth_user_id}' ID) current password with new password."
        )
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception(
            f"Failed to change user ('{auth_user_id}' ID) current password with new password!"
        )
        raise http_errors.InternalServerError(
            message="Failed to change your account current password with new password!"
        )

    _response = BaseResponse(
        request=request,
        message="Successfully changed your account current password with new password.",
        content=_user_dict,
    )
    if user_change_password.logout_all:
        _response.delete_cookie(key="access_token")
        _response.delete_cookie(key="refresh_token")

    return _response


@router.delete(
    "/",
    summary="Delete My Account",
    response_model=BaseResPM,
    responses={401: {}, 403: {}, 404: {}, 422: {}},
)
async def delete_me(
    request: Request,
    password: SecretStr = Body(
        ...,
        min_length=config.api.security.password.min_length,
        max_length=config.api.security.password.max_length,
        title="Password",
        description="Password to delete my account.",
        embed=True,
        examples=["your_password"],  # pragma: allowlist secret
    ),
    auth_user_id: str = Security(
        auth_deps.get_jwt_sub,
        scopes=[f"{_RESOURCE_NAME}:write", f"{_RESOURCE_NAME}:delete"],
    ),
    db_session: AsyncSession = Depends(db_deps.async_get_write),
):
    _logger: Logger = request.state.logger
    _logger.info(f"Deleting user ('{auth_user_id}' ID) account...")

    _user_dict: dict[str, Any] = {"id": auth_user_id}
    try:
        await service.async_delete_me(
            async_session=db_session,
            id_=auth_user_id,
            password=password,
            logger=_logger,
        )
        await db_session.commit()

        _logger.success(f"Successfully deleted user ('{auth_user_id}' ID) account.")
    except Exception as err:
        await db_session.rollback()

        if isinstance(err, HTTPException):
            raise

        _logger.exception(f"Failed to delete user ('{auth_user_id}' ID) account!")
        raise http_errors.InternalServerError(message="Failed to delete your account!")

    _response = BaseResponse(
        request=request,
        message="Successfully deleted your account, it will be deleted permanently in 30 days.",
        content=_user_dict,
    )
    return _response


__all__ = ["router"]
