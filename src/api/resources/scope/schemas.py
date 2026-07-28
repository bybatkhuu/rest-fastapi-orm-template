import sys
from enum import Enum
from typing import Any, Annotated

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from pydantic import Field, ConfigDict, model_validator
from pydantic.types import StringConstraints

from potato_util.constants import ALPHANUM_EMPTY_EXTEND_REGEX, ALPHANUM_SCOPE_REGEX

from api.core.schemas import (
    IdPM,
    TimestampPM,
    BasePM,
    BaseResPM,
    LinksResPM,
    PageLinksResPM,
)
from api.config import config

_scopes_base_url = f"{config.api.prefix}/scopes"


class ScopeOrderByEnum(str, Enum):
    VALUE = "value"
    PROTECTED = "protected"
    UPDATED_AT = "updated_at"
    CREATED_AT = "created_at"


class ScopeExpEnum(str, Enum):
    roles = "roles"
    # role_scopes = "role_scopes"


# Scopes
class ScopeBasePM(BasePM):
    description: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, max_length=256, pattern=ALPHANUM_EMPTY_EXTEND_REGEX
        ),
    ] = Field(
        default="",
        title="Description",
        description="Description of the scope.",
        examples=["This is a simple description of the scope."],
    )


class ScopeUpPM(ScopeBasePM):
    pass


class ScopeInPM(ScopeBasePM):
    value: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=2,
            max_length=128,
            pattern=ALPHANUM_SCOPE_REGEX,
        ),
    ] = Field(
        ...,
        title="Value",
        description="Value of the scope.",
        examples=["me:read"],
    )
    protected: bool = Field(
        default=False,
        title="Protected",
        description="Indicates the scope is protected and cannot be deleted or updated.",
        examples=[False],
    )


class ScopeOutPM(TimestampPM, ScopeInPM, IdPM):
    roles: list[dict[str, Any]] | None = Field(
        default=None,
        title="Roles",
        description="List of roles related to the scope.",
    )

    model_config = ConfigDict(from_attributes=True)


class ScopesOutPM(ScopeOutPM):
    links: LinksResPM = Field(
        default_factory=LinksResPM,
        title="Links",
        description="Links related to the current scope.",
        examples=[
            {
                "self": f"{_scopes_base_url}/sco1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5"
            }
        ],
    )

    @model_validator(mode="after")
    def _check_links(self) -> Self:
        self.links.self_link = f"{_scopes_base_url}/{self.id}"
        return self


class ResScopePM(BaseResPM):
    data: ScopeOutPM = Field(  # type: ignore
        ...,
        title="Scope Data",
        description="Scope as a main data.",
        examples=[
            {
                "id": "sco1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5",  # pragma: allowlist secret
                "value": "me:read",
                "protected": True,
                "description": "This is a simple description of the scope.",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "created_at": "2026-01-01T00:00:00+00:00",
                "roles": [],
            }
        ],
    )


class ResScopesPM(BaseResPM):
    data: list[ScopesOutPM] = Field(
        default=[],
        title="List of Scopes",
        description="List of scopes as main data.",
        examples=[
            [
                {
                    "id": "sco1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5",  # pragma: allowlist secret
                    "value": "me:read",
                    "protected": True,
                    "description": "This is a simple description of the scope.",
                    "updated_at": "2026-01-01T00:00:00+00:00",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "links": {
                        "self": f"{_scopes_base_url}/sco1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5"
                    },
                    "roles": [],
                },
                {
                    "id": "sco1699854600504660_337fc34be4304e14a193f6a2793ad9d1",
                    "value": "me:all",
                    "protected": False,
                    "description": "",
                    "updated_at": "2026-01-01T00:00:00+00:00",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "links": {
                        "self": f"{_scopes_base_url}/sco1699854600504660_337fc34be4304e14a193f6a2793ad9d1"
                    },
                    "roles": [],
                },
            ]
        ],
    )
    links: PageLinksResPM = Field(  # type: ignore
        default_factory=PageLinksResPM,
        title="Pagination Links",
        description="Pagination links for the list of scopes.",
        examples=[
            {
                "first": f"{_scopes_base_url}?skip=0&limit=10&is_desc=True",
                "prev": f"{_scopes_base_url}?skip=30&limit=10&is_desc=True",
                "self": f"{_scopes_base_url}?skip=40&limit=10&is_desc=True",
                "next": f"{_scopes_base_url}?skip=50&limit=10&is_desc=True",
                "last": f"{_scopes_base_url}?skip=90&limit=10&is_desc=True",
            }
        ],
    )


# Scopes

__all__ = [
    "ScopeExpEnum",
    "ScopeOrderByEnum",
    "ScopeBasePM",
    "ScopeInPM",
    "ScopeUpPM",
    "ScopeOutPM",
    "ScopesOutPM",
    "ResScopePM",
    "ResScopesPM",
]
