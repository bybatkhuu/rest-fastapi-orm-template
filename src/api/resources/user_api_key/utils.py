from pydantic import SecretStr

from potato_util.dt import now_utc_dt
from potato_util.generator import gen_random_string

from api.config import config


def build_api_key_prefix() -> str:
    """Build a API key prefix.

    Returns:
        str: Built API key prefix.
    """

    _key_prefix_template = config.api.security.api_key.prefix
    if "{timestamp}" in _key_prefix_template:
        _ts_seconds = int(now_utc_dt().timestamp())
        _key_prefix = _key_prefix_template.format(timestamp=_ts_seconds)
    else:
        _key_prefix = _key_prefix_template

    return _key_prefix


def generate_api_key() -> tuple[str, SecretStr, SecretStr]:
    """Generate a API key.

    Returns:
        tuple[str, SecretStr, SecretStr]: API key prefix, raw API key and full API key as tuple.
            - API key prefix as str.
            - Raw API key as SecretStr.
            - Full API key as SecretStr.
    """

    _key_prefix = build_api_key_prefix()
    _separator = config.api.security.api_key.separator
    _raw_api_key = SecretStr(
        gen_random_string(length=config.api.security.api_key.length)
    )
    _full_api_key = SecretStr(
        f"{_key_prefix}{_separator}{_raw_api_key.get_secret_value()}"
    )
    return _key_prefix, _raw_api_key, _full_api_key


__all__ = [
    "build_api_key_prefix",
    "generate_api_key",
]
