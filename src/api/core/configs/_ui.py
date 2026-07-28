from pydantic import Field, AnyHttpUrl
from pydantic_settings import SettingsConfigDict

from api.core.constants import ENV_PREFIX_API

from ._base import FrozenBaseConfig

_ENV_PREFIX_UI = f"{ENV_PREFIX_API}UI_"


class UIAuthConfig(FrozenBaseConfig):
    enabled: bool = Field(default=False)
    signup_url: AnyHttpUrl = Field(
        default_factory=lambda: AnyHttpUrl("https://auth.example.com/signup")
    )
    verify_url: AnyHttpUrl = Field(
        default_factory=lambda: AnyHttpUrl("https://auth.example.com/verify")
    )
    forgot_password_url: AnyHttpUrl = Field(
        default_factory=lambda: AnyHttpUrl("https://auth.example.com/forgot-password")
    )
    reset_password_url: AnyHttpUrl = Field(
        default_factory=lambda: AnyHttpUrl("https://auth.example.com/reset-password")
    )

    model_config = SettingsConfigDict(env_prefix=f"{_ENV_PREFIX_UI}AUTH_")


class UIConfig(FrozenBaseConfig):
    auth: UIAuthConfig = Field(default_factory=UIAuthConfig)

    model_config = SettingsConfigDict(env_prefix=_ENV_PREFIX_UI)


__all__ = [
    "UIAuthConfig",
    "UIConfig",
]
