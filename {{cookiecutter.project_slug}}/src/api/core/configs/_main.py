import os
import sys

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from pydantic import Field, field_validator, ValidationInfo, model_validator
from pydantic_settings import SettingsConfigDict

from potato_util.constants import EnvEnum

from api.core.constants import ENV_PREFIX, ENV_PREFIX_DB

from ._base import BaseMainConfig
from ._uvicorn import UvicornConfig, FrozenUvicornConfig
from ._db import DbConfig, FrozenDbConfig
from ._api import ApiConfig, FrozenApiConfig


# Main config schema:
class MainConfig(BaseMainConfig):
    env: EnvEnum = Field(default=EnvEnum.LOCAL, alias="env")
    debug: bool = Field(default=False, alias="debug")
    db: DbConfig = Field(default_factory=DbConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)

    @field_validator("api", mode="after")
    @classmethod
    def _check_api(cls, val: ApiConfig, info: ValidationInfo) -> FrozenApiConfig:
        _uvicorn: UvicornConfig = val.uvicorn
        if ("env" in info.data) and (info.data["env"] == EnvEnum.DEVELOPMENT):
            _uvicorn.reload = True

        if val.security.ssl.enabled:
            if not _uvicorn.ssl_keyfile:
                _uvicorn.ssl_keyfile = os.path.join(
                    val.paths.ssl_dir, val.security.ssl.key_fname
                )

            if not _uvicorn.ssl_certfile:
                _uvicorn.ssl_certfile = os.path.join(
                    val.paths.ssl_dir, val.security.ssl.cert_fname
                )

        _uvicorn = FrozenUvicornConfig(**_uvicorn.model_dump())
        val = FrozenApiConfig(uvicorn=_uvicorn, **val.model_dump(exclude={"uvicorn"}))
        return val

    @field_validator("db")
    @classmethod
    def _check_db(cls, val: DbConfig, info: ValidationInfo) -> FrozenDbConfig:
        if ("debug" in info.data) and (not info.data["debug"]):
            os.environ.pop(f"{ENV_PREFIX_DB}ECHO_SQL", None)
            val.echo_sql = False

            os.environ.pop(f"{ENV_PREFIX_DB}ECHO_POOL", None)
            val.echo_pool = False

        val = FrozenDbConfig(**val.model_dump())
        return val

    @model_validator(mode="after")
    def _check_required_envs(self) -> Self:
        _required_envs = [
            # f"{ENV_PREFIX_API}SECURITY_JWT_SECRET",
        ]

        if (self.env == EnvEnum.STAGING) or (self.env == EnvEnum.PRODUCTION):
            if (f"{ENV_PREFIX_DB}DSN_URL" not in os.environ) and (
                f"{ENV_PREFIX_DB}HOST" not in os.environ
                or f"{ENV_PREFIX_DB}PORT" not in os.environ
                or f"{ENV_PREFIX_DB}USERNAME" not in os.environ
                or f"{ENV_PREFIX_DB}PASSWORD" not in os.environ
                or f"{ENV_PREFIX_DB}DATABASE" not in os.environ
            ):
                raise KeyError(
                    f"Missing required '{ENV_PREFIX_DB}*' environment variables for STAGING/PRODUCTION environment!"
                )

            for _required_env in _required_envs:
                if _required_env not in os.environ:
                    raise ValueError(
                        f"Missing required '{_required_env}' environment variable for STAGING/PRODUCTION environment!"
                    )

        return self

    model_config = SettingsConfigDict(
        env_prefix=ENV_PREFIX,
        env_nested_delimiter="__",
        cli_prefix="",
        secrets_dir="/run/secrets",
        secrets_prefix="",
        secrets_nested_delimiter="_",
        secrets_dir_missing="ok",  # pragma: allowlist secret
    )  # type: ignore


__all__ = [
    "MainConfig",
]
