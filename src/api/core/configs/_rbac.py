from typing import Any

from pydantic import Field
from pydantic_settings import SettingsConfigDict
from api.core.constants import ENV_PREFIX_API

from ._base import FrozenBaseConfig

DEFAULT_SCOPES = {
    # admin:
    "all",
    # auth
    "auth:all",
    "auth:userinfo",
    # scopes
    "scopes:all",
    "scopes:read",
    "scopes:write",
    "scopes:create",
    "scopes:update",
    "scopes:delete",
    "scopes:protection",
    # roles
    "roles:all",
    "roles:write",
    "roles:read",
    "roles:create",
    "roles:update",
    "roles:delete",
    "roles:protection",
    # users
    "users:all",
    "users:read",
    "users:write",
    "users:create",
    "users:update",
    "users:delete",
    "users:password",
    "users:protection",
    # user me
    "me:all",
    "me:read",
    "me:write",
    "me:update",
    "me:delete",
    "me:password",
    # api-keys
    "me:api-keys:all",
    "me:api-keys:read",
    "me:api-keys:write",
    "me:api-keys:create",
    "me:api-keys:update",
    "me:api-keys:delete",
    "me:api-keys:revoke",
}

DEFAULT_ROLES = [
    {
        "name": "admin",
        "source": "INTERNAL",
        "protected": True,
        "scopes": ["all"],
    },
    {
        "name": "user",
        "source": "INTERNAL",
        "protected": True,
        "scopes": ["auth:userinfo", "me:all", "me:api-keys:all"],
    },
]


class RBACConfig(FrozenBaseConfig):
    scopes: set[str] = Field(default=DEFAULT_SCOPES)
    roles: list[dict[str, Any]] = Field(default=DEFAULT_ROLES)

    model_config = SettingsConfigDict(env_prefix=f"{ENV_PREFIX_API}RBAC_")


__all__ = [
    "DEFAULT_SCOPES",
    "DEFAULT_ROLES",
    "RBACConfig",
]
