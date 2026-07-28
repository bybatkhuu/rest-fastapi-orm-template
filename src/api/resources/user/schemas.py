import sys
from enum import Enum
from typing import Any, Annotated
from ipaddress import IPv4Address

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from pydantic import (
    Field,
    ConfigDict,
    EmailStr,
    SecretStr,
    AwareDatetime,
    field_validator,
    model_validator,
)
from pydantic.types import StringConstraints
from pydantic_extra_types.timezone_name import TimeZoneName

from potato_util.constants import (
    ALPHANUM_EXTEND_REGEX,
    ALPHANUM_TEXT_REGEX,
    ALPHANUM_HYPHEN_REGEX,
)
from potato_util.generator import gen_random_string

from api.core.schemas import (
    IdPM,
    TimestampPM,
    BasePM,
    BaseResPM,
    LinksResPM,
    PageLinksResPM,
)
from api.helpers.faker import fake
from api.config import config

_users_base_url = f"{config.api.prefix}/users"


class UserOrderByEnum(str, Enum):
    NICKNAME = "nickname"
    EMAIL = "email"
    STATUS = "status"
    PROTECTED = "protected"
    DELETED_AT = "deleted_at"
    UPDATED_AT = "updated_at"
    CREATED_AT = "created_at"


class UserExpEnum(str, Enum):
    roles = "roles"


class UserStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    DISABLED = "DISABLED"
    DELETED = "DELETED"


class UserStatusInEnum(str, Enum):
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"


class UserStatusUpEnum(str, Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


# Users
class UserBasePM(BasePM):
    nickname: Annotated[
        str | None,
        StringConstraints(
            strip_whitespace=True,
            min_length=1,
            max_length=64,
            pattern=ALPHANUM_EXTEND_REGEX,
        ),
    ] = Field(
        default=None,
        title="Nickname",
        description="Nickname for the user.",
        examples=["User 1"],
    )
    timezone: TimeZoneName = Field(
        default_factory=lambda: TimeZoneName("UTC"),
        title="Timezone",
        description="Timezone from IANA database format.",
        examples=["UTC"],
    )
    note: Annotated[
        str | None,
        StringConstraints(
            strip_whitespace=True, max_length=1024, pattern=ALPHANUM_TEXT_REGEX
        ),
    ] = Field(
        default=None,
        title="Note",
        description="Any note for the user.",
        examples=[""],
    )
    meta: dict[str, Any] | None = Field(
        default=None,
        title="Meta",
        description="Any metadata for the user.",
        examples=[{}],
    )


class UserUpPM(UserBasePM):
    status: UserStatusUpEnum = Field(
        default=UserStatusUpEnum.ACTIVE,
        title="Status",
        description="Status of the user.",
        examples=[UserStatusUpEnum.ACTIVE],
    )

    roles: set[
        Annotated[
            str,
            StringConstraints(
                strip_whitespace=True,
                min_length=2,
                max_length=64,
                pattern=ALPHANUM_HYPHEN_REGEX,
            ),
        ]
    ] = Field(
        default_factory=set,
        title="Roles",
        description="Roles of the user.",
        examples=[{"user"}],
    )


class UserInPM(UserBasePM):
    email: EmailStr = Field(
        ...,
        title="Email",
        description="Email address of the user.",
        examples=["user@example.com"],
    )
    password: SecretStr | None = Field(
        default=None,
        min_length=config.api.security.password.min_length,
        max_length=config.api.security.password.max_length,
        title="Password",
        description="Password for the user.",
        examples=["your_password"],  # pragma: allowlist secret
    )
    status: UserStatusInEnum = Field(
        default=UserStatusInEnum.ACTIVE,
        title="Status",
        description="Status of the user.",
        examples=[UserStatusInEnum.ACTIVE],
    )
    protected: bool = Field(
        default=False,
        title="Protected",
        description="Indicates the user is protected and cannot be deleted or updated.",
        examples=[False],
    )

    roles: set[
        Annotated[
            str,
            StringConstraints(
                strip_whitespace=True,
                min_length=2,
                max_length=64,
                pattern=ALPHANUM_HYPHEN_REGEX,
            ),
        ]
    ] = Field(
        default={config.api.user.role},
        title="Roles",
        description="Roles of the user.",
        examples=[{"user"}],
    )

    @field_validator("password", mode="after")
    @classmethod
    def _check_password(cls, val: SecretStr | None) -> SecretStr:
        if not val:
            val = SecretStr(gen_random_string(length=32, is_alphanum=False))

        return val

    @field_validator("nickname", mode="after")
    @classmethod
    def _check_nickname(cls, val: str | None) -> str:
        if (not val) or (not val.strip()):
            val = fake.user_name()

        return val

    @field_validator("roles", mode="after")
    @classmethod
    def _check_roles(cls, val: set[str]) -> set[str]:
        if not val:
            val = {config.api.user.role}

        return val


class UserPM(UserBasePM):
    email: EmailStr = Field(
        ...,
        title="Email",
        description="Email address of the user.",
        examples=["user@example.com"],
    )
    status: UserStatusEnum = Field(
        default=UserStatusEnum.ACTIVE,
        title="Status",
        description="Status of the user.",
        examples=[UserStatusEnum.ACTIVE],
    )
    protected: bool = Field(
        default=False,
        title="Protected",
        description="Indicates the user is protected and cannot be deleted or updated.",
        examples=[False],
    )
    last_login_ip: IPv4Address | None = Field(
        default=None,
        title="Last Login IP",
        description="Last login IP address of the user.",
        examples=["127.0.0.1"],
    )
    last_login_at: AwareDatetime | None = Field(
        default=None,
        title="Last Login At",
        description="Datetime when the user last logged in.",
        examples=["2026-01-01T00:00:00+00:00"],
    )
    verified_at: AwareDatetime | None = Field(
        default=None,
        title="Verified At",
        description="Datetime when the user is verified.",
        examples=["2026-01-01T00:00:00+00:00"],
    )
    deleted_at: AwareDatetime | None = Field(
        default=None,
        title="Deleted At",
        description="Datetime when the user is deleted.",
        examples=["2026-01-01T00:00:00+00:00"],
    )


class UserOutPM(TimestampPM, UserPM, IdPM):
    roles: set[str] | None = Field(
        default=None,
        title="Roles",
        description="Set of roles related to the user.",
        examples=[{"user", "admin"}],
    )

    @field_validator("roles", mode="before")
    @classmethod
    def _check_roles(cls, val: Any) -> set[str]:
        _roles = set[str]()
        if val and isinstance(val, list):
            for _role in val:
                if isinstance(_role, dict) and ("name" in _role):
                    _roles.add(_role.get("name", ""))

        return _roles

    model_config = ConfigDict(from_attributes=True)


class UsersOutPM(UserOutPM):
    links: LinksResPM = Field(
        default_factory=LinksResPM,
        title="Links",
        description="Links related to the current user.",
        examples=[
            {
                "self": f"{_users_base_url}/use1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5"
            }
        ],
    )

    @model_validator(mode="after")
    def _check_links(self) -> Self:
        self.links.self_link = f"{_users_base_url}/{self.id}"
        return self


class ResUserPM(BaseResPM):
    data: UserOutPM = Field(  # type: ignore
        ...,
        title="User Data",
        description="User as a main data.",
        examples=[
            {
                "id": "use1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5",  # pragma: allowlist secret
                "nickname": "User 1",
                "email": "user@example.com",
                "status": "ACTIVE",
                "timezone": "UTC",
                "protected": True,
                "last_login_ip": "127.0.0.1",
                "last_login_at": "2026-01-01T00:00:00+00:00",
                "verified_at": "2026-01-01T00:00:00+00:00",
                "deleted_at": None,
                "note": "Note for the user.",
                "meta": {"key": "value"},
                "updated_at": "2026-01-01T00:00:00+00:00",
                "created_at": "2026-01-01T00:00:00+00:00",
                "roles": {"user"},
            }
        ],
    )


class ResUsersPM(BaseResPM):
    data: list[UsersOutPM] = Field(
        default=[],
        title="List of Users",
        description="List of users as main data.",
        examples=[
            [
                {
                    "id": "use1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5",  # pragma: allowlist secret
                    "nickname": "User 1",
                    "email": "user@example.com",
                    "status": "ACTIVE",
                    "timezone": "UTC",
                    "protected": True,
                    "last_login_ip": "127.0.0.1",
                    "last_login_at": "2026-01-01T00:00:00+00:00",
                    "verified_at": "2026-01-01T00:00:00+00:00",
                    "deleted_at": None,
                    "note": "Note for the user.",
                    "meta": {"key": "value"},
                    "updated_at": "2026-01-01T00:00:00+00:00",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "links": {
                        "self": f"{_users_base_url}/use1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5"
                    },
                    "roles": {"user"},
                },
                {
                    "id": "use1699854600504660_337fc34be4304e14a193f6a2793ad9d1",
                    "nickname": "User 2",
                    "email": "user2@example.com",
                    "status": "PENDING",
                    "timezone": "Asia/Seoul",
                    "protected": False,
                    "last_login_ip": None,
                    "last_login_at": None,
                    "verified_at": None,
                    "deleted_at": None,
                    "note": None,
                    "meta": None,
                    "updated_at": "2026-01-01T00:00:00+00:00",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "links": {
                        "self": f"{_users_base_url}/use1699854600504660_337fc34be4304e14a193f6a2793ad9d1"
                    },
                    "roles": {"admin"},
                },
            ]
        ],
    )
    links: PageLinksResPM = Field(  # type: ignore
        default_factory=PageLinksResPM,
        title="Pagination Links",
        description="Pagination links for the list of users.",
        examples=[
            {
                "first": f"{_users_base_url}?skip=0&limit=10&is_desc=True",
                "prev": f"{_users_base_url}?skip=30&limit=10&is_desc=True",
                "self": f"{_users_base_url}?skip=40&limit=10&is_desc=True",
                "next": f"{_users_base_url}?skip=50&limit=10&is_desc=True",
                "last": f"{_users_base_url}?skip=90&limit=10&is_desc=True",
            }
        ],
    )


# Users

__all__ = [
    "UserExpEnum",
    "UserOrderByEnum",
    "UserStatusEnum",
    "UserStatusInEnum",
    "UserStatusUpEnum",
    "UserBasePM",
    "UserInPM",
    "UserUpPM",
    "UserPM",
    "UserOutPM",
    "UsersOutPM",
    "ResUserPM",
    "ResUsersPM",
]
