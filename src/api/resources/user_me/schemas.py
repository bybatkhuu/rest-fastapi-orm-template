import sys
from typing import Annotated

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from pydantic import Field, SecretStr, model_validator
from pydantic.types import StringConstraints
from pydantic_extra_types.timezone_name import TimeZoneName

from potato_util.constants import ALPHANUM_EXTEND_REGEX

from api.core.schemas import BasePM
from api.config import config


class UserMeUpPM(BasePM):
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


class UserMeChangePasswordPM(BasePM):
    current_password: SecretStr = Field(
        ...,
        min_length=config.api.security.password.min_length,
        max_length=config.api.security.password.max_length,
        title="Current Password",
        description="Current password of the user.",
        examples=["your_password"],  # pragma: allowlist secret
    )
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
    logout_all: bool | None = Field(
        default=None,
        title="Logout All",
        description="Logout from all logged in sessions of the user.",
        examples=[False],
    )

    @model_validator(mode="after")
    def _validate_password(self) -> Self:
        if self.password.get_secret_value() != self.password_confirm.get_secret_value():
            raise ValueError("Password and confirm password does not match!")

        return self


__all__ = [
    "UserMeUpPM",
    "UserMeChangePasswordPM",
]
