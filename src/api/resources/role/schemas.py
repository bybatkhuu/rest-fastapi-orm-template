import sys
from enum import Enum
from typing import Any, Annotated

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from pydantic import Field, ConfigDict, model_validator, field_validator
from pydantic.types import StringConstraints

from potato_util.constants import (
    ALPHANUM_HYPHEN_REGEX,
    ALPHANUM_EMPTY_EXTEND_REGEX,
    ALPHANUM_SCOPE_REGEX,
)

from api.core.schemas import (
    IdPM,
    TimestampPM,
    BasePM,
    BaseResPM,
    LinksResPM,
    PageLinksResPM,
)
from api.config import config

_roles_base_url = f"{config.api.prefix}/roles"


class RoleOrderByEnum(str, Enum):
    NAME = "name"
    SOURCE = "source"
    PROTECTED = "protected"
    UPDATED_AT = "updated_at"
    CREATED_AT = "created_at"


class RoleExpEnum(str, Enum):
    scopes = "scopes"
    user_roles = "user_roles"


class RoleSourceEnum(str, Enum):
    INTERNAL = "INTERNAL"


# Roles
class RoleBasePM(BasePM):
    source: RoleSourceEnum = Field(
        default=RoleSourceEnum.INTERNAL,
        title="Source",
        description="Source of the role.",
        examples=[RoleSourceEnum.INTERNAL],
    )
    description: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, max_length=256, pattern=ALPHANUM_EMPTY_EXTEND_REGEX
        ),
    ] = Field(
        default="",
        title="Description",
        description="Description of the role.",
        examples=["This is a simple description of the role."],
    )


class RoleUpPM(RoleBasePM):
    scopes: set[
        Annotated[
            str,
            StringConstraints(
                strip_whitespace=True,
                min_length=2,
                max_length=128,
                pattern=ALPHANUM_SCOPE_REGEX,
            ),
        ]
    ] = Field(
        default_factory=set,
        title="Scopes",
        description="Scopes of the role.",
        examples=[{"me:read", "me:write"}],
    )


class RolePM(RoleBasePM):
    name: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=2,
            max_length=64,
            pattern=ALPHANUM_HYPHEN_REGEX,
        ),
    ] = Field(
        ...,
        title="Name",
        description="Name of the role.",
        examples=["user"],
    )
    protected: bool = Field(
        default=False,
        title="Protected",
        description="Indicates the role is protected and cannot be deleted or updated.",
        examples=[False],
    )


class RoleInPM(RolePM):
    scopes: set[
        Annotated[
            str,
            StringConstraints(
                strip_whitespace=True,
                min_length=2,
                max_length=128,
                pattern=ALPHANUM_SCOPE_REGEX,
            ),
        ]
    ] = Field(
        default_factory=set,
        title="Scopes",
        description="Scopes of the role.",
        examples=[{"me:read", "me:write"}],
    )


class RoleOutPM(TimestampPM, RolePM, IdPM):
    scopes: set[str] | None = Field(
        default=None,
        title="Scopes",
        description="Set of scopes related to the role.",
        examples=[{"me:read", "me:write"}],
    )

    user_roles: list[dict[str, Any]] | None = Field(
        default=None,
        title="User Roles",
        description="List of user roles related to the role.",
    )

    @field_validator("scopes", mode="before")
    @classmethod
    def _check_scopes(cls, val: Any) -> set[str]:
        _scopes = set[str]()
        if val and isinstance(val, list):
            for _scope in val:
                if isinstance(_scope, dict) and ("value" in _scope):
                    _scopes.add(_scope.get("value", ""))

        return _scopes

    model_config = ConfigDict(from_attributes=True)


class RolesOutPM(RoleOutPM):
    links: LinksResPM = Field(
        default_factory=LinksResPM,
        title="Links",
        description="Links related to the current role.",
        examples=[{"self": f"{_roles_base_url}/user"}],
    )

    @model_validator(mode="after")
    def _check_links(self) -> Self:
        self.links.self_link = f"{_roles_base_url}/{self.name}"
        return self


class ResRolePM(BaseResPM):
    data: RoleOutPM = Field(  # type: ignore
        ...,
        title="Role Data",
        description="Role as a main data.",
        examples=[
            {
                "id": "rol1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5",  # pragma: allowlist secret
                "name": "user",
                "source": "INTERNAL",
                "protected": True,
                "description": "This is a simple description of the role.",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "created_at": "2026-01-01T00:00:00+00:00",
                "scopes": {"me:read", "me:write"},
                "user_roles": [],
            }
        ],
    )


class ResRolesPM(BaseResPM):
    data: list[RolesOutPM] = Field(
        default=[],
        title="List of Roles",
        description="List of roles as main data.",
        examples=[
            [
                {
                    "id": "rol1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5",  # pragma: allowlist secret
                    "name": "user",
                    "source": "INTERNAL",
                    "protected": True,
                    "description": "This is a simple description of the role.",
                    "updated_at": "2026-01-01T00:00:00+00:00",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "links": {"self": f"{_roles_base_url}/user"},
                    "scopes": {"me:read", "me:write"},
                    "user_roles": [],
                },
                {
                    "id": "rol1699854600504660_337fc34be4304e14a193f6a2793ad9d1",  # pragma: allowlist secret
                    "name": "manager",
                    "source": "INTERNAL",
                    "protected": False,
                    "description": "",
                    "updated_at": "2026-01-01T00:00:00+00:00",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "links": {"self": f"{_roles_base_url}/manager"},
                    "scopes": {"user:read"},
                    "user_roles": [],
                },
            ]
        ],
    )
    links: PageLinksResPM = Field(  # type: ignore
        default_factory=PageLinksResPM,
        title="Pagination Links",
        description="Pagination links for the list of roles.",
        examples=[
            {
                "first": f"{_roles_base_url}?skip=0&limit=10&is_desc=True",
                "prev": f"{_roles_base_url}?skip=30&limit=10&is_desc=True",
                "self": f"{_roles_base_url}?skip=40&limit=10&is_desc=True",
                "next": f"{_roles_base_url}?skip=50&limit=10&is_desc=True",
                "last": f"{_roles_base_url}?skip=90&limit=10&is_desc=True",
            }
        ],
    )


# Roles

__all__ = [
    "RoleExpEnum",
    "RoleSourceEnum",
    "RoleBasePM",
    "RoleInPM",
    "RoleUpPM",
    "RoleOutPM",
    "RolesOutPM",
    "ResRolePM",
    "ResRolesPM",
]
