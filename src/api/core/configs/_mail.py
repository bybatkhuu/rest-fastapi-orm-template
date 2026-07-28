from pydantic import EmailStr, NameEmail, SecretStr, Field
from pydantic_settings import SettingsConfigDict

from api.core.constants import ENV_PREFIX_MAIL

from ._base import FrozenBaseConfig


class MailConfig(FrozenBaseConfig):
    host: str = Field(default="smtp.gmail.com", min_length=2, max_length=256)
    port: int = Field(default=465, ge=25, le=65535)
    username: EmailStr | str = Field(default="support@example.com")
    password: SecretStr = Field(
        default_factory=lambda: SecretStr(f"{ENV_PREFIX_MAIL}PASSWORD123")
    )
    starttls: bool = Field(default=False)
    from_addr: NameEmail = Field(
        default_factory=lambda: NameEmail("No Reply", "no-reply@example.com")
    )

    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX_MAIL)


__all__ = ["MailConfig"]
