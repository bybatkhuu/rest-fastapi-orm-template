import os
from typing_extensions import Self

from pydantic import Field, constr, field_validator, ValidationInfo, model_validator
from pydantic_settings import SettingsConfigDict

from beans_logging import LoggerConfigPM

from api.__version__ import __version__
from api.core.constants import EnvEnum, ENV_PREFIX, ENV_PREFIX_API, ENV_PREFIX_DB
from api.core.utils import validator
from ._base import FrozenBaseConfig
from ._db import DbConfig, FrozenDbConfig
from ._dev import DevConfig, FrozenDevConfig
from ._api import ApiConfig, FrozenApiConfig


# Main config schema:
class MainConfig(FrozenBaseConfig):
    env: EnvEnum = Field(...)
    debug: bool = Field(...)
    version: constr(strip_whitespace=True) = Field(  # type: ignore
        default=__version__, min_length=3, max_length=32
    )
    db: DbConfig = Field(...)
    api: ApiConfig = Field(...)
    logger: LoggerConfigPM = Field(default_factory=LoggerConfigPM)

    @field_validator("env")
    @classmethod
    def _check_env(cls, val: EnvEnum) -> EnvEnum:
        _env = "ENV"
        if _env in os.environ:
            _env = os.getenv(_env).upper()
            val = EnvEnum(_env)

        return val

    @field_validator("debug")
    @classmethod
    def _check_debug(cls, val: str) -> str:
        _debug_env = "DEBUG"
        if _debug_env in os.environ:
            val = os.getenv(_debug_env)
            val = validator.is_truthy(val)

        return val

    @field_validator("version")
    @classmethod
    def _check_version(cls, val: str) -> str:
        val = __version__
        return val

    @field_validator("api")
    @classmethod
    def _check_api(cls, val: ApiConfig, info: ValidationInfo) -> FrozenApiConfig:
        _dev: DevConfig = val.dev
        if ("env" in info.data) and (info.data["env"] == EnvEnum.DEVELOPMENT):
            _dev.reload = True

        _dev = FrozenDevConfig(**_dev.model_dump())
        val = FrozenApiConfig(dev=_dev, **val.model_dump(exclude={"dev"}))
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

    @field_validator("logger")
    @classmethod
    def _check_logger(cls, val: LoggerConfigPM, info: ValidationInfo) -> LoggerConfigPM:
        if "api" in info.data:
            if not val.app_name:
                val.app_name = info.data["api"].slug
            elif "{api_slug}" in val.app_name:
                val.app_name = val.app_name.format(api_slug=info.data["api"].slug)

        _logs_dir_env = f"{ENV_PREFIX_API}LOGS_DIR"
        if _logs_dir_env in os.environ:
            val.file.logs_dir = os.getenv(_logs_dir_env)

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

    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX, env_nested_delimiter="__")


__all__ = ["MainConfig"]
