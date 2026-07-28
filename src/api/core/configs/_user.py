from typing import Any

from pydantic import Field, EmailStr, SecretStr, field_validator
from pydantic_settings import SettingsConfigDict
from pydantic_extra_types.timezone_name import TimeZoneName

from potato_util.generator import gen_unique_id, gen_random_string

from api.core.constants import ENV_PREFIX_API
from api.helpers.faker import fake

from ._base import FrozenBaseConfig

_ENV_PREFIX_USER = f"{ENV_PREFIX_API}USER_"


class UserBaseConfig(FrozenBaseConfig):
    id: str | None = Field(default=None, min_length=8, max_length=64)
    nickname: str | None = Field(default=None, min_length=2, max_length=64)
    email: EmailStr = Field(default="user@example.com")
    password: SecretStr = Field(
        default_factory=lambda: SecretStr(
            gen_random_string(length=32, is_alphanum=False)
        ),
        min_length=8,
        max_length=128,
    )
    timezone: TimeZoneName = Field(default_factory=lambda: TimeZoneName("UTC"))
    roles: list[str] = Field(default=["user"])
    protected: bool = Field(default=True)

    @field_validator("id", mode="before")
    @classmethod
    def _check_id(cls, val: Any) -> str:
        if (not val) or (isinstance(val, str) and (not val.strip())):
            val = gen_unique_id(prefix="use")

        return val

    @field_validator("nickname", mode="before")
    @classmethod
    def _check_nickname(cls, val: Any) -> str:
        if (not val) or (isinstance(val, str) and (not val.strip())):
            val = fake.user_name()

        return val


class AdminConfig(UserBaseConfig):
    model_config = SettingsConfigDict(env_prefix=f"{_ENV_PREFIX_USER}ADMIN_")


class UserConfig(FrozenBaseConfig):
    role: str = Field(default="user", min_length=2, max_length=64)
    users: list[UserBaseConfig] = Field(
        default=[
            AdminConfig(
                nickname="Admin",
                email="admin@example.com",
                password=SecretStr(f"{_ENV_PREFIX_USER}ADMIN_PASSWORD123"),
                timezone=TimeZoneName("UTC"),
                roles=["admin"],
                protected=True,
            ),
            # UserBaseConfig(
            #     nickname="User",
            #     email="user@example.com",
            #     timezone=TimeZoneName("UTC"),
            #     roles=["user"],
            #     protected=True,
            # ),
        ]
    )

    model_config = SettingsConfigDict(env_prefix=_ENV_PREFIX_USER)


__all__ = ["UserConfig"]
