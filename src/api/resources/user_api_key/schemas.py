import sys
from enum import Enum
from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network
from typing import Annotated

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from pydantic import Field, model_validator, ConfigDict, AwareDatetime, field_validator
from pydantic.types import StringConstraints

from potato_util.constants import (
    ALPHANUM_EXTEND_REGEX,
    ALPHANUM_HYPHEN_REGEX,
    ALPHANUM_SCOPE_REGEX,
)
from potato_util.dt import now_utc_dt

from api.core.schemas import (
    IdPM,
    TimestampPM,
    BasePM,
    BaseResPM,
    LinksResPM,
    PageLinksResPM,
)
from api.config import config

_api_keys_base_url = f"{config.api.prefix}/api-keys"


class ApiKeyStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class ApiKeyStatusUpEnum(str, Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


# ApiKey
class ApiKeyBasePM(BasePM):
    name: Annotated[
        str | None,
        StringConstraints(
            strip_whitespace=True,
            min_length=2,
            max_length=64,
            pattern=ALPHANUM_EXTEND_REGEX,
        ),
    ] = Field(
        default=None,
        title="Name",
        description="Human-readable name for the API key.",
        examples=["API Key 1"],
    )
    allowed_scopes: set[
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
        title="Allowed Scopes",
        description="Scopes granted to this API key. Empty means inherit all scopes from the user.",
        examples=[{"me:read", "me:write"}],
    )
    allowed_ips: set[IPv4Address | IPv6Address | IPv4Network | IPv6Network] = Field(
        default_factory=set,
        title="Allowed IPs",
        description="IPs allowed to use this API key. Empty means allow from any IP.",
        examples=[{"127.0.0.1", "192.168.1.0/24"}],
    )


class ApiKeyInPM(ApiKeyBasePM):
    expires_at: AwareDatetime | None = Field(
        default=None,
        title="Expires At",
        description="Datetime when the API key expires.",
        examples=["2027-01-01T00:00:00+00:00"],
    )

    @field_validator("expires_at", mode="after")
    @classmethod
    def _check_expires_at(cls, val: AwareDatetime | None) -> AwareDatetime | None:
        if val and (val <= now_utc_dt()):
            raise ValueError(
                "'expires_at' is in the past, it should be future than the current datetime!"
            )

        return val


class ApiKeyUpPM(ApiKeyBasePM):
    status: ApiKeyStatusUpEnum = Field(
        default=ApiKeyStatusUpEnum.ACTIVE,
        title="Status",
        description="Status of the API key.",
        examples=[ApiKeyStatusUpEnum.ACTIVE],
    )


class ApiKeyPM(ApiKeyBasePM):
    key_prefix: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=2,
            max_length=16,
            pattern=ALPHANUM_HYPHEN_REGEX,
        ),
    ] = Field(
        ...,
        title="Key Prefix",
        description="Prefix of the API key for security and searchability.",
        examples=["sk-1735689600"],
    )
    expires_at: AwareDatetime | None = Field(
        default=None,
        title="Expires At",
        description="Datetime when the API key expires.",
        examples=["2027-01-01T00:00:00+00:00"],
    )
    status: ApiKeyStatusEnum = Field(
        default=ApiKeyStatusEnum.ACTIVE,
        title="Status",
        description="Status of the API key.",
        examples=["ACTIVE"],
    )
    revoked_at: AwareDatetime | None = Field(
        default=None,
        title="Revoked At",
        description="Datetime when the API key is revoked.",
        examples=["2026-01-01T00:00:00+00:00"],
    )
    last_used_ip: IPv4Address | IPv6Address | None = Field(
        default=None,
        title="Last Used IP",
        description="IP address the API key was last used from.",
        examples=["127.0.0.1"],
    )
    last_used_at: AwareDatetime | None = Field(
        default=None,
        title="Last Used At",
        description="Datetime the API key was last used.",
        examples=["2026-01-01T00:00:00+00:00"],
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
        description="ID of the user related to this API key.",
        examples=[
            "use1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5"  # pragma: allowlist secret
        ],
    )


class ApiKeyOutPM(TimestampPM, ApiKeyPM, IdPM):
    model_config = ConfigDict(from_attributes=True)


class ApiKeyCreatedOutPM(ApiKeyOutPM):
    api_key: str = Field(
        ...,
        title="Full API Key",
        description="Full API key as a plain text.",
        examples=["sk-1735689600.rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5"],
    )


class ApiKeysOutPM(ApiKeyOutPM):
    links: LinksResPM = Field(
        default_factory=LinksResPM,
        title="Links",
        description="Links related to the current API key.",
        examples=[
            {
                "self": f"{_api_keys_base_url}/uak1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5"
            }
        ],
    )

    @model_validator(mode="after")
    def _check_links(self) -> Self:
        self.links.self_link = f"{_api_keys_base_url}/{self.id}"
        return self


class ResApiKeyPM(BaseResPM):
    data: ApiKeyOutPM = Field(  # type: ignore
        ...,
        title="API Key Data",
        description="API key as a main data.",
        examples=[
            {
                "id": "uak1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5",  # pragma: allowlist secret
                "name": "API Key 1",
                "key_prefix": "sk-1735689600",
                "status": "ACTIVE",
                "allowed_scopes": {"me:read", "me:write"},
                "allowed_ips": {"127.0.0.1", "192.168.1.0/24"},
                "expires_at": "2026-01-01T00:00:00+00:00",
                "revoked_at": None,
                "last_used_ip": "127.0.0.1",
                "last_used_at": "2026-01-01T00:00:00+00:00",
                "user_id": "use1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "created_at": "2026-01-01T00:00:00+00:00",
            }
        ],
    )


class ResCreatedApiKeyPM(BaseResPM):
    data: ApiKeyCreatedOutPM = Field(  # type: ignore
        ...,
        title="Created API Key Data",
        description="Created API key as a main data.",
        examples=[
            {
                "id": "uak1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5",  # pragma: allowlist secret
                "name": "API Key 1",
                "key_prefix": "sk-1735689600",
                "api_key": "sk-1735689600.a2b57qvquiim7kfvexg605ue1px67r6y",  # pragma: allowlist secret
                "status": "ACTIVE",
                "allowed_scopes": {"me:read", "me:write"},
                "allowed_ips": {"127.0.0.1", "192.168.1.0/24"},
                "expires_at": "2026-01-01T00:00:00+00:00",
                "revoked_at": None,
                "last_used_ip": "127.0.0.1",
                "last_used_at": "2026-01-01T00:00:00+00:00",
                "user_id": "use1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "created_at": "2026-01-01T00:00:00+00:00",
            }
        ],
    )


class ResApiKeysPM(BaseResPM):
    data: list[ApiKeysOutPM] = Field(
        default=[],
        title="List of API Keys",
        description="List of API keys as main data.",
        examples=[
            [
                {
                    "id": "uak1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5",  # pragma: allowlist secret
                    "name": "API Key 1",
                    "key_prefix": "sk-1735689600",
                    "status": "ACTIVE",
                    "allowed_scopes": {"me:read", "me:write"},
                    "allowed_ips": {"127.0.0.1", "192.168.1.0/24"},
                    "expires_at": "2026-01-01T00:00:00+00:00",
                    "revoked_at": None,
                    "last_used_ip": "127.0.0.1",
                    "last_used_at": "2026-01-01T00:00:00+00:00",
                    "user_id": "use1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5",
                    "updated_at": "2026-01-01T00:00:00+00:00",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "links": {
                        "self": f"{_api_keys_base_url}/uak1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5"
                    },
                },
                {
                    "id": "uak1699854600504660_337fc34be4304e14a193f6a2793ad9d1",
                    "name": "API Key 2",
                    "key_prefix": "sk-1735689600",
                    "status": "REVOKED",
                    "allowed_scopes": {"me:read"},
                    "allowed_ips": {"127.0.0.1", "192.168.1.10/32"},
                    "expires_at": "2026-01-01T00:00:00+00:00",
                    "revoked_at": "2026-01-01T00:00:00+00:00",
                    "last_used_ip": "127.0.0.1",
                    "last_used_at": "2026-01-01T00:00:00+00:00",
                    "user_id": "use1699854600504660_337fc34be4304e14a193f6a2793ad9d1",
                    "updated_at": "2026-01-01T00:00:00+00:00",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "links": {
                        "self": f"{_api_keys_base_url}/uak1699854600504660_337fc34be4304e14a193f6a2793ad9d1"
                    },
                },
            ]
        ],
    )
    links: PageLinksResPM = Field(  # type: ignore
        default_factory=PageLinksResPM,
        title="Pagination Links",
        description="Pagination links for the list of API keys.",
        examples=[
            {
                "first": f"{_api_keys_base_url}?skip=0&limit=10&is_desc=True",
                "prev": f"{_api_keys_base_url}?skip=30&limit=10&is_desc=True",
                "self": f"{_api_keys_base_url}?skip=40&limit=10&is_desc=True",
                "next": f"{_api_keys_base_url}?skip=50&limit=10&is_desc=True",
                "last": f"{_api_keys_base_url}?skip=90&limit=10&is_desc=True",
            }
        ],
    )


__all__ = [
    "ApiKeyStatusEnum",
    "ApiKeyBasePM",
    "ApiKeyInPM",
    "ApiKeyUpPM",
    "ApiKeyPM",
    "ApiKeyOutPM",
    "ApiKeysOutPM",
    "ApiKeyCreatedOutPM",
    "ResApiKeyPM",
    "ResCreatedApiKeyPM",
    "ResApiKeysPM",
    "ApiKeyStatusUpEnum",
]
