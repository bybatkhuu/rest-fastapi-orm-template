import sys
import uuid
from enum import Enum
from typing import Annotated

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from pydantic import (
    Field,
    SecretStr,
    EmailStr,
    AwareDatetime,
    model_validator,
    field_validator,
    field_serializer,
)
from pydantic.types import StringConstraints
from pydantic_extra_types.timezone_name import TimeZoneName

from potato_util.constants import ALPHANUM_EXTEND_REGEX, JWT_REGEX
from potato_util.dt import now_utc_dt, calc_future_dt
from potato_util.validator import is_valid

from api.core.schemas import BasePM, ExtraBasePM
from api.helpers.faker import fake
from api.config import config


class TokenTypeHintEnum(str, Enum):
    access_token = "access_token"  # nosec B105
    refresh_token = "refresh_token"  # nosec B105
    verify_token = "verify_token"  # nosec B105
    reset_token = "reset_token"  # nosec B105


class TokenRevokeTypeEnum(str, Enum):
    refresh_token = "refresh_token"  # nosec B105
    reset_token = "reset_token"  # nosec B105


class TokenGrantTypeEnum(str, Enum):
    refresh_token = "refresh_token"  # nosec B105
    # authorization_code = "authorization_code"
    # client_credentials = "client_credentials"


class UserPasswordInPM(BasePM):
    password: SecretStr = Field(
        ...,
        min_length=config.api.security.password.min_length,
        max_length=config.api.security.password.max_length,
        title="Password",
        description="Password for the user.",
        examples=["your_password"],  # pragma: allowlist secret
    )
    password_confirm: SecretStr = Field(
        ...,
        min_length=config.api.security.password.min_length,
        max_length=config.api.security.password.max_length,
        title="Confirm Password",
        description="Confirm password to check if the password is correct.",
        examples=["your_password"],  # pragma: allowlist secret
    )

    @model_validator(mode="after")
    def _validate_password(self) -> Self:
        if self.password.get_secret_value() != self.password_confirm.get_secret_value():
            raise ValueError("Password and confirm password does not match!")

        return self


class UserSignupPM(UserPasswordInPM):
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
    email: EmailStr = Field(
        ...,
        title="Email",
        description="Email address of the user.",
        examples=["user@example.com"],
    )
    timezone: TimeZoneName | None = Field(
        default=None,
        title="Timezone",
        description="Timezone from IANA database format.",
        examples=["UTC"],
    )

    @model_validator(mode="after")
    def _check_all(self) -> Self:
        if (not self.nickname) or (not self.nickname.strip()):
            self.nickname = fake.user_name()

        if not self.timezone:
            self.timezone = TimeZoneName("UTC")

        return self


class UserLoginPM(BasePM):
    email: EmailStr = Field(
        ...,
        title="Email",
        description="Email address of the user.",
        examples=["user@example.com"],
    )
    password: SecretStr = Field(
        ...,
        min_length=config.api.security.password.min_length,
        max_length=config.api.security.password.max_length,
        title="Password",
        description="Password of the user to login.",
        examples=["your_password"],  # pragma: allowlist secret
    )
    remember_me: bool | None = Field(
        default=None,
        title="Remember Me",
        description="Remember the user for a longer period of time.",
        examples=[False, True],
    )


class UserResetPasswordPM(UserPasswordInPM):
    reset_token: SecretStr = Field(
        ...,
        min_length=16,
        max_length=4096,
        title="Reset Token",
        description="Token to reset the user password.",
        examples=[
            (
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwia"
                "WF0IjoxNTE2MjM5MDIyfQ.t42p4AHef69Tyyi88U6-p0utZYYrg7mmCGhoAd7Zffs"
            )
        ],
    )
    logout_all: bool | None = Field(
        default=None,
        title="Logout All",
        description="Logout from all logged in sessions of the user.",
        examples=[True, False],
    )

    @field_validator("reset_token", mode="after")
    @classmethod
    def _validate_reset_token(cls, val: SecretStr) -> SecretStr:
        if not is_valid(val=val.get_secret_value(), pattern=JWT_REGEX):
            raise ValueError("Invalid reset token!")

        return val


class JWTPayloadPM(ExtraBasePM):
    sub: str = Field(
        ...,
        title="Subject",
        description="Subject of the token.",
        examples=[
            "use1699928748406213_rqsjaqd3zfrjsvph71p5ttp3eyxvxyb5"  # pragma: allowlist secret
        ],
    )
    exp: AwareDatetime | None = Field(
        default=None,
        title="Expiration Time",
        description="Expiration time of the token.",
        examples=["2026-01-01T00:00:00+00:00"],
    )
    iat: AwareDatetime = Field(
        default_factory=now_utc_dt,
        title="Issued At",
        description="Issued at time of the token.",
        examples=["2026-01-01T00:00:00+00:00"],
    )
    jti: str = Field(
        default_factory=lambda: uuid.uuid4().hex,
        title="JWT ID",
        description="JWT ID of the token.",
        examples=["123e4567e89b12d3a456426614174000"],  # pragma: allowlist secret
    )
    typ: TokenTypeHintEnum = Field(
        ...,
        title="Token Type",
        description="Type of the token.",
        examples=[TokenTypeHintEnum.access_token],
    )

    @model_validator(mode="after")
    def _check_exp(self) -> Self:
        if not self.exp:
            _duration = 0
            if self.typ == TokenTypeHintEnum.access_token:
                _duration = config.api.security.jwt.access_duration
            elif self.typ == TokenTypeHintEnum.verify_token:
                _duration = config.api.security.jwt.verify_duration
            elif self.typ == TokenTypeHintEnum.reset_token:
                _duration = config.api.security.token.reset_duration
            elif self.typ == TokenTypeHintEnum.refresh_token:
                _duration = config.api.security.token.refresh_duration

            self.exp = calc_future_dt(dt=self.iat, delta=_duration)

        return self


class SecretTokenPayloadPM(JWTPayloadPM):
    token: SecretStr = Field(...)


class AccessTokenPayloadPM(JWTPayloadPM):
    typ: TokenTypeHintEnum = Field(default=TokenTypeHintEnum.access_token)
    nickname: str | None = Field(default=None)
    email: EmailStr = Field(...)
    email_verified: bool = Field(...)
    timezone: TimeZoneName = Field(...)
    roles: set[str] = Field(...)
    scopes: set[str] = Field(...)

    @field_serializer("roles")
    def _serialize_roles(self, val: set[str]) -> list[str]:
        _val = list[str](val)
        return _val

    @field_serializer("scopes")
    def _serialize_scopes(self, val: set[str]) -> list[str]:
        _val = list[str](val)
        return _val


class AuthTokensOutPM(BasePM):
    token_type: str = Field(
        default="bearer",
        title="Token Type",
        description="Type of the token.",
        examples=["bearer"],
    )
    access_token: str = Field(
        ...,
        title="Access Token",
        description="Access token to authenticate.",
        examples=[
            (
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwia"  # nosec B105
                "WF0IjoxNTE2MjM5MDIyfQ.t42p4AHef69Tyyi88U6-p0utZYYrg7mmCGhoAd7Zffs"  # nosec B105
            )
        ],
    )
    expires_in: int = Field(
        default=config.api.security.jwt.access_duration,
        title="Expires In",
        description="Access token expires in seconds.",
        examples=[600],
    )
    scopes: set[str] = Field(
        ...,
        title="Scopes",
        description="Scopes of the access token.",
        examples=[{"me:read", "me:write"}],
    )
    refresh_token: str | None = Field(
        default=None,
        title="Refresh Token",
        description="Refresh token to refresh the access token.",
        examples=[
            (
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwia"  # nosec B105
                "WF0IjoxNTE2MjM5MDIyfQ.t42p4AHef69Tyyi88U6-p0utZYYrg7mmCGhoAd7Zffs"  # nosec B105
            ),
        ],
    )

    @field_serializer("scopes")
    def _serialize_scopes(self, val: set[str]) -> list[str]:
        _val = list[str](val)
        return _val


class IntrospectOutPM(ExtraBasePM):
    active: bool = Field(
        ...,
        title="Is Active",
        description="Whether the token is active or not.",
        examples=[False],
    )
    reason: str | None = Field(
        default=None,
        title="Reason",
        description="Reason why the token is not active.",
        examples=["token_expired"],
    )


__all__ = [
    "TokenTypeHintEnum",
    "TokenRevokeTypeEnum",
    "TokenGrantTypeEnum",
    "UserSignupPM",
    "UserLoginPM",
    "UserResetPasswordPM",
    "JWTPayloadPM",
    "SecretTokenPayloadPM",
    "AccessTokenPayloadPM",
    "AuthTokensOutPM",
    "IntrospectOutPM",
]
