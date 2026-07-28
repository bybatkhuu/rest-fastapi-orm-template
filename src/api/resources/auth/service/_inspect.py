from typing import Any, cast
from collections.abc import Collection

from pydantic import validate_call, SecretStr
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from potato_util.constants import WarnEnum
from potato_util import deep_merge

from api.resources.user.model import UserORM
from api.resources.user import service as user_service
from api.resources.user_token.schemas import UserTokenKindEnum, UserTokenStatusEnum
from api.resources.user_token import service as user_token_service
from api.logger import Logger, logger

from ..schemas import TokenTypeHintEnum, SecretTokenPayloadPM
from .. import utils as auth_utils


@validate_call(config={"arbitrary_types_allowed": True})
async def async_introspect(
    async_session: AsyncSession,
    token: SecretStr,
    token_type_hint: TokenTypeHintEnum,
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> dict[str, Any]:
    """Introspect token."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Inspecting '{token_type_hint}' type token...")

    _output_dict: dict[str, Any] = {"active": False}
    try:
        _jwt_payload = await auth_utils.async_verify_jwt(
            token=token, jwt_type=token_type_hint
        )
    except ExpiredSignatureError:
        logger.warning(
            f"[ANOMALY] - Attempting to inspect '{token_type_hint}' type token but it's expired!"
        )
        _output_dict["reason"] = "token_expired"
        return _output_dict
    except InvalidTokenError:
        logger.warning(
            f"[ANOMALY] - Attempting to inspect '{token_type_hint}' type token but it's invalid!"
        )
        _output_dict["reason"] = "token_invalid"
        return _output_dict

    if (token_type_hint == TokenTypeHintEnum.access_token) or (
        token_type_hint == TokenTypeHintEnum.verify_token
    ):
        _output_dict["active"] = True
        _output_dict = deep_merge(_output_dict, _jwt_payload.model_dump(mode="json"))
    else:
        _kind = UserTokenKindEnum(token_type_hint.value.replace("_token", "").upper())
        _user_id = _jwt_payload.sub

        assert isinstance(
            _jwt_payload, SecretTokenPayloadPM
        ), "JWT payload should be a SecretTokenPayloadPM!"

        _token_secret = _jwt_payload.token
        _user_token_orm = await user_token_service.async_get_by_token(
            async_session=async_session,
            token=_token_secret,
            user_id=_user_id,
            kind=_kind,
            logger=logger,
            warn_mode=WarnEnum.DEBUG,
        )

        if not _user_token_orm:
            logger.warning(
                f"[ANOMALY] - Attempting to inspect '{token_type_hint}' type token but not found token "
                "itself from the database!"
            )
            _output_dict["reason"] = "token_invalid"
            return _output_dict

        if _user_token_orm.status == UserTokenStatusEnum.ACTIVE:
            _output_dict["active"] = True
            _output_dict = deep_merge(
                _output_dict, _jwt_payload.model_dump(mode="json")
            )
        elif _user_token_orm.status == UserTokenStatusEnum.EXPIRED:
            _output_dict["reason"] = "token_expired"
        elif _user_token_orm.status == UserTokenStatusEnum.USED:
            _output_dict["reason"] = "token_used"
        else:
            _output_dict["reason"] = "token_invalid"

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully inspected '{token_type_hint}' type token.")

    return _output_dict


@validate_call(config={"arbitrary_types_allowed": True})
async def async_userinfo(
    async_session: AsyncSession,
    user_id: str,
    joins: Collection[str] | list[str] | set[str] = {"roles"},
    logger: Logger = logger,
    warn_mode: WarnEnum = WarnEnum.IGNORE,
) -> dict[str, Any]:
    """Get user info by ID."""

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Getting user info of the user with '{user_id}' ID...")

    if "roles" not in joins:
        if isinstance(joins, list):
            joins.append("roles")
        elif isinstance(joins, set):
            joins.add("roles")

    _user_orm = cast(
        UserORM,
        await user_service.async_get(
            async_session=async_session,
            id_=user_id,
            joins=joins,
            logger=logger,
            warn_mode=WarnEnum.DEBUG,
        ),
    )
    _user_dict = _user_orm.to_dict(load_relations=joins)

    if warn_mode == WarnEnum.DEBUG:
        logger.debug(f"Successfully got the user info of the user with '{user_id}' ID.")

    return _user_dict


__all__ = [
    "async_introspect",
    "async_userinfo",
]
