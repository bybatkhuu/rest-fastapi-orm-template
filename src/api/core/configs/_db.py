from urllib.parse import quote_plus
from typing import Any, Dict, Optional, Union

from pydantic import Field, conint, constr, SecretStr, model_validator
from pydantic_settings import SettingsConfigDict

from api.core.constants import ENV_PREFIX_DB

from ._base import BaseConfig


class DbConfig(BaseConfig):
    dialect: constr(strip_whitespace=True) = Field(..., min_length=2, max_length=32)  # type: ignore
    driver: constr(strip_whitespace=True) = Field(..., min_length=2, max_length=32)  # type: ignore

    host: constr(strip_whitespace=True) = Field(..., min_length=2, max_length=128)  # type: ignore
    port: int = Field(..., ge=100, le=65535)
    username: constr(strip_whitespace=True) = Field(..., min_length=2, max_length=32)  # type: ignore
    password: SecretStr = Field(..., min_length=8, max_length=64)
    database: constr(strip_whitespace=True) = Field(..., min_length=2, max_length=128)  # type: ignore
    dsn_url: SecretStr | None = Field(default=None)

    read_host: None | (
        constr(strip_whitespace=True, min_length=2, max_length=128)  # type: ignore
    ) = Field(default=None)
    read_port: conint(ge=100, le=65535) | None = Field(default=None)  # type: ignore
    read_username: None | (
        constr(strip_whitespace=True, min_length=2, max_length=32)  # type: ignore
    ) = Field(default=None)
    read_password: SecretStr | None = Field(default=None, min_length=8, max_length=64)  # type: ignore
    read_database: None | (
        constr(strip_whitespace=True, min_length=2, max_length=128)  # type: ignore
    ) = Field(default=None)
    read_dsn_url: SecretStr | None = Field(default=None)

    connect_args: dict[str, Any] | None = Field(default=None)
    prefix: constr(strip_whitespace=True) = Field(..., max_length=16)  # type: ignore
    max_try_connect: int = Field(..., ge=1, le=100)
    retry_after: int = Field(..., ge=1, le=600)
    echo_sql: bool | constr(strip_whitespace=True, pattern=r"^(debug)$") = Field(...)  # type: ignore
    echo_pool: bool | constr(strip_whitespace=True, pattern=r"^(debug)$") = Field(  # type: ignore
        ...
    )
    pool_size: int = Field(..., ge=0, le=1000)  # 0 means no limit
    max_overflow: int = Field(
        ..., ge=0, le=1000
    )  # pool_size + max_overflow = max number of pools allowed
    pool_recycle: int = Field(..., ge=-1, le=86_400)  # 3 hours, -1 means no timeout
    pool_timeout: int = Field(..., ge=0, le=3600)  # 30 seconds
    select_limit: int = Field(..., ge=1, le=100_000)
    select_max_limit: int = Field(..., ge=1, le=10_000_000)
    select_is_desc: bool = Field(...)

    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX_DB)


class FrozenDbConfig(DbConfig):
    @model_validator(mode="before")
    @classmethod
    def _check_all(cls, values: dict[str, Any]) -> dict[str, Any]:
        _dsn_url_template = (
            "{dialect}+{driver}://{username}:{password}@{host}:{port}/{database}"
        )

        if not values["dsn_url"]:
            _password = values["password"]
            if isinstance(_password, SecretStr):
                _password = _password.get_secret_value()

            _encoded_password = quote_plus(_password)
            values["dsn_url"] = _dsn_url_template.format(
                dialect=values["dialect"],
                driver=values["driver"],
                username=values["username"],
                password=_encoded_password,
                host=values["host"],
                port=values["port"],
                database=values["database"],
            )

        if not values["read_dsn_url"]:
            _read_password = ""
            if values["read_password"]:
                _read_password = values["read_password"]
                if isinstance(_read_password, SecretStr):
                    _read_password = _read_password.get_secret_value()
            else:
                _read_password = values["password"]
                if isinstance(_read_password, SecretStr):
                    _read_password = quote_plus(_read_password.get_secret_value())

            _encoded_read_password = quote_plus(_read_password)
            values["read_dsn_url"] = _dsn_url_template.format(
                dialect=values["dialect"],
                driver=values["driver"],
                username=values["read_username"] or values["username"],
                password=_encoded_read_password,
                host=values["read_host"] or values["host"],
                port=values["read_port"] or values["port"],
                database=values["read_database"] or values["database"],
            )

        return values

    model_config = SettingsConfigDict(frozen=True)


__all__ = ["DbConfig", "FrozenDbConfig"]
