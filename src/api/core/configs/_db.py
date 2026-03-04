from typing import Any
from urllib.parse import quote_plus

from pydantic import Field, constr, SecretStr, model_validator
from pydantic_settings import SettingsConfigDict

from api.core.constants import ENV_PREFIX, ENV_PREFIX_DB

from ._base import BaseConfig


class DbConfig(BaseConfig):
    dialect: str = Field(default="postgresql", min_length=2, max_length=32)
    driver: str = Field(default="psycopg", min_length=2, max_length=32)

    host: str = Field(default="localhost", min_length=2, max_length=128)
    port: int = Field(default=5432, ge=100, le=65535)
    username: str = Field(
        default=f"{ENV_PREFIX.lower()}admin", min_length=2, max_length=32
    )
    password: SecretStr = Field(
        default_factory=lambda: SecretStr(f"{ENV_PREFIX}DB_PASSWORD123"),
        min_length=8,
        max_length=64,
    )
    database: str = Field(
        default=f"{ENV_PREFIX.lower()}db", min_length=2, max_length=128
    )
    dsn_url: SecretStr | None = Field(default=None)

    read_host: str | None = Field(default=None, min_length=2, max_length=128)
    read_port: int | None = Field(default=None, ge=100, le=65535)
    read_username: str | None = Field(default=None, min_length=2, max_length=32)
    read_password: SecretStr | None = Field(default=None, min_length=8, max_length=64)
    read_database: str | None = Field(default=None, min_length=2, max_length=128)
    read_dsn_url: SecretStr | None = Field(default=None)

    connect_args: dict[str, Any] | None = Field(default={"sslmode": "prefer"})
    prefix: str = Field(default=f"{ENV_PREFIX.lower()}", max_length=16)
    max_try_connect: int = Field(default=3, ge=1, le=100)
    retry_after: int = Field(default=4, ge=1, le=600)
    echo_sql: bool | constr(strip_whitespace=True, pattern=r"^(debug)$") = Field(  # type: ignore # noqa: F722
        default=False
    )
    echo_pool: bool | constr(strip_whitespace=True, pattern=r"^(debug)$") = Field(  # type: ignore # noqa: F722
        default=False
    )
    pool_size: int = Field(default=10, ge=0, le=1000)  # 0 means no limit
    max_overflow: int = Field(
        default=10, ge=0, le=1000
    )  # pool_size + max_overflow = max number of pools allowed
    pool_recycle: int = Field(
        default=10800, ge=-1, le=86_400
    )  # 3 hours, -1 means no timeout
    pool_timeout: int = Field(default=30, ge=0, le=3600)  # 30 seconds
    select_limit: int = Field(default=100, ge=1, le=100_000)
    select_max_limit: int = Field(default=100000, ge=1, le=10_000_000)
    select_is_desc: bool = Field(default=True)

    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX_DB)


class FrozenDbConfig(DbConfig):
    @model_validator(mode="before")
    @classmethod
    def _check_all(cls, data: Any) -> Any:
        if isinstance(data, dict):
            _dsn_url_template = (
                "{dialect}+{driver}://{username}:{password}@{host}:{port}/{database}"
            )

            if ("dsn_url" in data) and (not data["dsn_url"]):
                _password = data["password"]
                if isinstance(_password, SecretStr):
                    _password = _password.get_secret_value()

                _encoded_password = quote_plus(_password)
                data["dsn_url"] = _dsn_url_template.format(
                    dialect=data["dialect"],
                    driver=data["driver"],
                    username=data["username"],
                    password=_encoded_password,
                    host=data["host"],
                    port=data["port"],
                    database=data["database"],
                )

            if ("read_dsn_url" in data) and (not data["read_dsn_url"]):
                _read_password = ""
                if data["read_password"]:
                    _read_password = data["read_password"]
                    if isinstance(_read_password, SecretStr):
                        _read_password = _read_password.get_secret_value()
                else:
                    _read_password = data["password"]
                    if isinstance(_read_password, SecretStr):
                        _read_password = quote_plus(_read_password.get_secret_value())

                _encoded_read_password = quote_plus(_read_password)
                data["read_dsn_url"] = _dsn_url_template.format(
                    dialect=data["dialect"],
                    driver=data["driver"],
                    username=data["read_username"] or data["username"],
                    password=_encoded_read_password,
                    host=data["read_host"] or data["host"],
                    port=data["read_port"] or data["port"],
                    database=data["read_database"] or data["database"],
                )

        return data

    model_config = SettingsConfigDict(frozen=True)


__all__ = ["DbConfig", "FrozenDbConfig"]
