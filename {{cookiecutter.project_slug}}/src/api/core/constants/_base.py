ENV_PREFIX = "{{cookiecutter.env_prefix}}"
ENV_PREFIX_API = f"{ENV_PREFIX}API_"
ENV_PREFIX_DB = f"{ENV_PREFIX}DB_"

API_SLUG = "{{cookiecutter.project_slug}}"


__all__ = [
    "ENV_PREFIX",
    "ENV_PREFIX_API",
    "ENV_PREFIX_DB",
    "API_SLUG",
]
