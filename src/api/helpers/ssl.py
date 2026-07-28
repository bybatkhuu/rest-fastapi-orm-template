import os

from potato_util.crypto import ssl as ssl_utils

from api.config import config
from api.logger import logger


def check_ssl_certs() -> None:
    """Check if SSL certificates exist when SSL is enabled or set to be generated.

    Raises:
        SystemExit: If SSL certificates are missing or cannot be created.
    """

    if config.api.security.ssl.generate:
        ssl_utils.create_ssl_certs(
            ssl_dir=config.api.paths.ssl_dir,
            key_fname=config.api.security.ssl.key_fname,
            cert_fname=config.api.security.ssl.cert_fname,
            key_size=config.api.security.ssl.key_size,
            x509_attrs=config.api.security.ssl.x509_attrs.model_dump(),
        )

    if config.api.security.ssl.enabled:
        _ssl_keyfile_path = os.path.join(
            config.api.paths.ssl_dir, config.api.security.ssl.key_fname
        )
        _ssl_certfile_path = os.path.join(
            config.api.paths.ssl_dir, config.api.security.ssl.cert_fname
        )

        if (not os.path.isfile(_ssl_keyfile_path)) or (
            not os.path.isfile(_ssl_certfile_path)
        ):
            logger.error("SSL key or certificate file not found!")
            raise SystemExit(1)

    return


__all__ = [
    "check_ssl_certs",
]
