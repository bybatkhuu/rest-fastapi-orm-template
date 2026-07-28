import sys
from enum import Enum
from ipaddress import IPv4Address, IPv6Address
from typing import Annotated

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from pydantic import Field, ConfigDict, AwareDatetime, SecretStr, model_validator
from pydantic.types import StringConstraints

from potato_util.constants import ALPHANUM_HYPHEN_REGEX

from api.core.schemas import (
    IdPM,
    TimestampPM,
    BasePM,
    BaseResPM,
    LinksResPM,
    PageLinksResPM,
)
from api.config import config

_user_tokens_base_url = f"{config.api.prefix}/user-tokens"


class UserTokenKindEnum(str, Enum):
    REFRESH = "REFRESH"
    RESET = "RESET"
    # AUTH_CODE = "AUTH_CODE"


class UserTokenStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    USED = "USED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    BLOCKED = "BLOCKED"


# UserToken
class UserTokenBasePM(BasePM):
    kind: UserTokenKindEnum = Field(
        ...,
        title="Kind",
        description="Kind of the user token.",
        examples=["REFRESH"],
    )
    expires_at: AwareDatetime = Field(
        ...,
        title="Expires At",
        description="Datetime when the user token expires.",
        examples=["2026-01-01T00:00:00+00:00"],
    )
    family_token_id: Annotated[
        str | None,
        StringConstraints(
            strip_whitespace=True,
            min_length=8,
            max_length=64,
            pattern=ALPHANUM_HYPHEN_REGEX,
        ),
    ] = Field(
        default=None,
        title="Family Token ID",
        description="ID of the family refresh token related to this user token.",
        examples=[
            "ust1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5"  # pragma: allowlist secret
        ],
    )
    user_id: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=8,
            max_length=64,
            pattern=ALPHANUM_HYPHEN_REGEX,
        ),
    ] = Field(
        ...,
        title="User ID",
        description="ID of the user related to this token.",
        examples=[
            "use1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5"  # pragma: allowlist secret
        ],
    )


class UserTokenUpPM(BasePM):
    status: UserTokenStatusEnum = Field(
        default=UserTokenStatusEnum.ACTIVE,
        title="Status",
        description="Status of the user token.",
        examples=["ACTIVE"],
    )
    revoked_at: AwareDatetime | None = Field(
        default=None,
        title="Revoked At",
        description="Datetime when the user token is revoked.",
        examples=["2026-01-01T00:00:00+00:00"],
    )
    used_at: AwareDatetime | None = Field(
        default=None,
        title="Used At",
        description="Datetime when the user token is used.",
        examples=["2026-01-01T00:00:00+00:00"],
    )
    used_ip: IPv4Address | IPv6Address | None = Field(
        default=None,
        title="Used IP",
        description="IP address when the user token is used.",
        examples=["127.0.0.1"],
    )


class UserTokenInPM(UserTokenBasePM):
    token: SecretStr = Field(
        ...,
        min_length=32,
        max_length=256,
        title="Token",
        description="Token value.",
        examples=[
            "gCW6J3scsWHY9esQ46O4HfAXf2OrWIXKk5QqBixKi1WVShOACa63egAYyV3D3K6o"  # pragma: allowlist secret
        ],
    )


class UserTokenPM(UserTokenBasePM, UserTokenUpPM):
    pass


class UserTokenOutPM(TimestampPM, UserTokenPM, IdPM):
    model_config = ConfigDict(from_attributes=True)


class UserTokensOutPM(UserTokenOutPM):
    links: LinksResPM = Field(
        default_factory=LinksResPM,
        title="Links",
        description="Links related to the current user token.",
        examples=[
            {
                "self": f"{_user_tokens_base_url}/ust1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5"
            }
        ],
    )

    @model_validator(mode="after")
    def _check_links(self) -> Self:
        self.links.self_link = f"{_user_tokens_base_url}/{self.id}"
        return self


class ResUserTokenPM(BaseResPM):
    data: UserTokenOutPM = Field(  # type: ignore
        ...,
        title="User Token Data",
        description="User token as a main data.",
        examples=[
            {
                "id": "ust1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5",  # pragma: allowlist secret
                "kind": "REFRESH",
                "status": "REVOKED",
                "expires_at": "2026-01-01T00:00:00+00:00",
                "revoked_at": "2026-01-01T00:00:00+00:00",
                "used_at": "2026-01-01T00:00:00+00:00",
                "used_ip": "127.0.0.1",
                "family_token_id": "ust1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5",  # nosec B105
                "user_id": "use1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "created_at": "2026-01-01T00:00:00+00:00",
            }
        ],
    )


class ResUserTokensPM(BaseResPM):
    data: list[UserTokensOutPM] = Field(
        default=[],
        title="List of User Tokens",
        description="List of user tokens as main data.",
        examples=[
            [
                {
                    "id": "ust1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5",  # pragma: allowlist secret
                    "kind": "REFRESH",
                    "status": "REVOKED",
                    "expires_at": "2026-01-01T00:00:00+00:00",
                    "revoked_at": "2026-01-01T00:00:00+00:00",
                    "used_at": "2026-01-01T00:00:00+00:00",
                    "used_ip": "127.0.0.1",
                    "family_token_id": "ust1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5",  # nosec B105
                    "user_id": "use1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5",
                    "updated_at": "2026-01-01T00:00:00+00:00",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "links": {
                        "self": f"{_user_tokens_base_url}/ust1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5"
                    },
                },
                {
                    "id": "ust1699854600504660_337fc34be4304e14a193f6a2793ad9d1",  # pragma: allowlist secret
                    "kind": "RESET",
                    "status": "ACTIVE",
                    "expires_at": "2026-01-01T00:00:00+00:00",
                    "revoked_at": None,
                    "used_at": None,
                    "used_ip": None,
                    "family_token_id": None,
                    "user_id": "use1699854600504660_337fc34be4304e14a193f6a2793ad9d1",  # nosec B105
                    "updated_at": "2026-01-01T00:00:00+00:00",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "links": {
                        "self": f"{_user_tokens_base_url}/ust1699854600504660_337fc34be4304e14a193f6a2793ad9d1"
                    },
                },
            ]
        ],
    )
    links: PageLinksResPM = Field(  # type: ignore
        default_factory=PageLinksResPM,
        title="Pagination Links",
        description="Pagination links for the list of user tokens.",
        examples=[
            {
                "first": f"{_user_tokens_base_url}?skip=0&limit=10&is_desc=True",
                "prev": f"{_user_tokens_base_url}?skip=30&limit=10&is_desc=True",
                "self": f"{_user_tokens_base_url}?skip=40&limit=10&is_desc=True",
                "next": f"{_user_tokens_base_url}?skip=50&limit=10&is_desc=True",
                "last": f"{_user_tokens_base_url}?skip=90&limit=10&is_desc=True",
            }
        ],
    )


# UserToken

__all__ = [
    "UserTokenKindEnum",
    "UserTokenStatusEnum",
    "UserTokenBasePM",
    "UserTokenUpPM",
    "UserTokenInPM",
    "UserTokenOutPM",
    "UserTokensOutPM",
    "ResUserTokenPM",
    "ResUserTokensPM",
]
