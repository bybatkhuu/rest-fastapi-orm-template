from pydantic import validate_call

_TABLE_PREFIX: str | None = None


@validate_call
def init_table_prefix(table_prefix: str) -> None:
    global _TABLE_PREFIX
    _TABLE_PREFIX = table_prefix
    return


def get_table_prefix() -> str:
    if _TABLE_PREFIX is None:
        raise RuntimeError("Database `TABLE_PREFIX` is not initialized!")

    return _TABLE_PREFIX


__all__ = [
    "init_table_prefix",
    "get_table_prefix",
]
