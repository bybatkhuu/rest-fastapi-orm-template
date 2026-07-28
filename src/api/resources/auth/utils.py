import os
from collections.abc import Collection

import jwt
from jwt.exceptions import InvalidTokenError
from pydantic import validate_call, SecretStr

from potato_util.crypto import asymmetric as asymmetric_utils

from api.config import config

from .schemas import (
    TokenTypeHintEnum,
    JWTPayloadPM,
    SecretTokenPayloadPM,
    AccessTokenPayloadPM,
)


@validate_call
async def async_gen_jwt(
    payload: JWTPayloadPM | SecretTokenPayloadPM | AccessTokenPayloadPM,
) -> SecretStr:
    """Asynchronously generate a JWT token for the user.

    Args:
        payload (JWTPayloadPM |
                 SecretTokenPayloadPM |
                 AccessTokenPayloadPM  , required): Payload for JWT token as Pydantic model.

    Returns:
        SecretStr: Generated JWT token as SecretStr.
    """

    _key = ""
    _algorithm = ""
    if payload.typ == TokenTypeHintEnum.access_token:
        _key = config.api.security.jwt.secret.get_secret_value()
        _algorithm = config.api.security.jwt.algorithm
    else:
        _private_key_path = os.path.join(
            config.api.paths.asymmetric_keys_dir,
            config.api.security.asymmetric.private_key_fname,
        )
        _key = await asymmetric_utils.async_get_private_key(
            private_key_path=_private_key_path
        )
        _algorithm = config.api.security.asymmetric.algorithm

    _payload = payload.model_dump()
    if isinstance(payload, SecretTokenPayloadPM):
        _payload["token"] = payload.token.get_secret_value()

    _token = SecretStr(jwt.encode(payload=_payload, key=_key, algorithm=_algorithm))
    return _token


@validate_call(config={"arbitrary_types_allowed": True})
async def async_verify_jwt(
    token: SecretStr,
    jwt_type: TokenTypeHintEnum | Collection[str] | None = None,
    verify_exp: bool = True,
) -> JWTPayloadPM | SecretTokenPayloadPM | AccessTokenPayloadPM:
    """Asynchronously verify the JWT token and return the payload.

    Args:
        token      (SecretStr                                 , required): JWT token to verify.
        jwt_type   (TokenTypeHintEnum | Collection[str] | None, optional): Indicates the type of JWT token.
        verify_exp (bool                                      , optional): Verify expiration time. Defaults to True.

    Raises:
        ExpiredSignatureError: If JWT token is expired.
        InvalidTokenError    : If JWT token is invalid.
        ValidationError      : If JWT payload is invalid.

    Returns:
        JWTPayloadPM | SecretTokenPayloadPM | AccessTokenPayloadPM  : Verified JWT payload as Pydantic model.
    """

    _key = ""
    _algorithm = ""
    if (not jwt_type) or (jwt_type == TokenTypeHintEnum.access_token):
        _key = config.api.security.jwt.secret.get_secret_value()
        _algorithm = config.api.security.jwt.algorithm
    else:
        _public_key_path = os.path.join(
            config.api.paths.asymmetric_keys_dir,
            config.api.security.asymmetric.public_key_fname,
        )
        _key = await asymmetric_utils.async_get_public_key(
            public_key_path=_public_key_path
        )
        _algorithm = config.api.security.asymmetric.algorithm

    _jwt_payload = jwt.decode(
        jwt=token.get_secret_value(),
        key=_key,
        algorithms=[_algorithm],
        options={
            "require": ["sub", "exp", "iat", "jti", "typ"],
            "verify_exp": verify_exp,
        },
    )

    _payload: JWTPayloadPM | SecretTokenPayloadPM | AccessTokenPayloadPM
    if not jwt_type:
        jwt_type = _jwt_payload.get("typ", "")

    if jwt_type == TokenTypeHintEnum.access_token:
        _payload = AccessTokenPayloadPM(**_jwt_payload)
    elif jwt_type == TokenTypeHintEnum.verify_token:
        _payload = JWTPayloadPM(**_jwt_payload)
    else:
        _payload = SecretTokenPayloadPM(**_jwt_payload)

    if jwt_type != _payload.typ:
        raise InvalidTokenError(f"Invalid token type: '{_payload.typ}'!")

    return _payload


@validate_call
def gen_jwt(
    payload: JWTPayloadPM | SecretTokenPayloadPM | AccessTokenPayloadPM,
) -> SecretStr:
    """Generate a JWT token for the user.

    Args:
        payload (JWTPayloadPM |
                 SecretTokenPayloadPM |
                 AccessTokenPayloadPM  , required): Payload for JWT token as Pydantic model.

    Returns:
        SecretStr: Generated JWT token as SecretStr.
    """

    _key = ""
    _algorithm = ""
    if payload.typ == TokenTypeHintEnum.access_token:
        _key = config.api.security.jwt.secret.get_secret_value()
        _algorithm = config.api.security.jwt.algorithm
    else:
        _private_key_path = os.path.join(
            config.api.paths.asymmetric_keys_dir,
            config.api.security.asymmetric.private_key_fname,
        )
        _key = asymmetric_utils.get_private_key(private_key_path=_private_key_path)
        _algorithm = config.api.security.asymmetric.algorithm

    _payload = payload.model_dump()
    if isinstance(payload, SecretTokenPayloadPM):
        _payload["token"] = payload.token.get_secret_value()

    _token = SecretStr(jwt.encode(payload=_payload, key=_key, algorithm=_algorithm))
    return _token


@validate_call(config={"arbitrary_types_allowed": True})
def verify_jwt(
    token: SecretStr,
    jwt_type: TokenTypeHintEnum | Collection[str] | None = None,
    verify_exp: bool = True,
) -> JWTPayloadPM | SecretTokenPayloadPM | AccessTokenPayloadPM:
    """Verify the JWT token and return the payload.

    Args:
        token      (SecretStr                                 , required): JWT token to verify.
        jwt_type   (TokenTypeHintEnum | Collection[str] | None, optional): Indicates the type of JWT token.
        verify_exp (bool                                      , optional): Verify expiration time. Defaults to True.

    Raises:
        ExpiredSignatureError: If JWT token is expired.
        InvalidTokenError    : If JWT token is invalid.
        ValidationError      : If JWT payload is invalid.

    Returns:
        JWTPayloadPM | SecretTokenPayloadPM |
                       AccessTokenPayloadPM  : Verified JWT payload as Pydantic model.
    """

    _key = ""
    _algorithm = ""
    if (not jwt_type) or (jwt_type == TokenTypeHintEnum.access_token):
        _key = config.api.security.jwt.secret.get_secret_value()
        _algorithm = config.api.security.jwt.algorithm
    else:
        _public_key_path = os.path.join(
            config.api.paths.asymmetric_keys_dir,
            config.api.security.asymmetric.public_key_fname,
        )
        _key = asymmetric_utils.get_public_key(public_key_path=_public_key_path)
        _algorithm = config.api.security.asymmetric.algorithm

    _jwt_payload = jwt.decode(
        jwt=token.get_secret_value(),
        key=_key,
        algorithms=[_algorithm],
        options={
            "require": ["sub", "exp", "iat", "jti", "typ"],
            "verify_exp": verify_exp,
        },
    )

    _payload: JWTPayloadPM | SecretTokenPayloadPM | AccessTokenPayloadPM
    if not jwt_type:
        jwt_type = _jwt_payload.get("typ", "")

    if jwt_type == TokenTypeHintEnum.access_token:
        _payload = AccessTokenPayloadPM(**_jwt_payload)
    elif jwt_type == TokenTypeHintEnum.verify_token:
        _payload = JWTPayloadPM(**_jwt_payload)
    else:
        _payload = SecretTokenPayloadPM(**_jwt_payload)

    if jwt_type != _payload.typ:
        raise InvalidTokenError(f"Invalid token type: '{_payload.typ}'!")

    return _payload


@validate_call
def make_verify_url(base_url: str, verify_token: SecretStr) -> SecretStr:
    """Makes verify URL with token.

    Args:
        base_url     (str      , required): Base URL to create URL with.
        verify_token (SecretStr, required): Verify token to create URL with.

    Returns:
        SecretStr: Verify URL with token.
    """

    _verify_url = f"{base_url}/verify"
    if config.ui.auth.enabled:
        _verify_url = config.ui.auth.verify_url

    _verify_url = SecretStr(f"{_verify_url}?token={verify_token.get_secret_value()}")
    return _verify_url


@validate_call
def make_reset_password_url(base_url: str, reset_token: SecretStr) -> SecretStr:
    """Makes reset URL with token.

    Args:
        base_url    (str      , required): Base URL to create URL with.
        reset_token (SecretStr, required): Reset token to create URL with.

    Returns:
        SecretStr: Reset URL with token.
    """

    _reset_password_url = f"{base_url}/reset-password"
    if config.ui.auth.enabled:
        _reset_password_url = config.ui.auth.reset_password_url

    _reset_password_url = SecretStr(
        f"{_reset_password_url}?token={reset_token.get_secret_value()}"
    )
    return _reset_password_url


__all__ = [
    "async_gen_jwt",
    "async_verify_jwt",
    "gen_jwt",
    "verify_jwt",
    "make_verify_url",
    "make_reset_password_url",
]
