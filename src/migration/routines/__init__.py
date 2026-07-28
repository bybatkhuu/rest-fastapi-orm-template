# flake8: noqa

from .functions import *
from .triggers import *


def create_all_tables_fn_tr() -> None:
    """Create all tables trigger functions."""

    _stat_table_names = [
        "fot_scope",
        "fot_role",
        "fot_role_scope",
        "fot_user",
        "fot_user_role",
        "fot_user_token",
        "fot_user_api_key",
    ]
    _all_table_names = _stat_table_names + ["fot_table_stat"]
    create_all_base_tr(table_names=_all_table_names)
    return


def drop_all_tables_fn() -> None:
    """Drop all tables functions."""

    return


__all__ = [
    "create_all_base_fn",
    "drop_all_base_fn",
    "create_all_tables_fn_tr",
    "drop_all_tables_fn",
]
