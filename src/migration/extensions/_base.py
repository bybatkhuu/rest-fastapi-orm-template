from alembic import op


def create_pg_stat_statements() -> None:
    """Create pg_stat_statements extension."""

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements;")
    return


def create_pg_cron() -> None:
    """Create pg_cron extension."""

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_cron;")
    return


def create_btree_gist() -> None:
    """Create btree_gist extension."""

    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist;")
    return


def create_all_ext() -> None:
    """Create all extensions."""

    create_pg_stat_statements()
    # create_pg_cron()
    # create_btree_gist()
    return


def drop_all_ext() -> None:
    """Drop all extensions."""

    op.execute("DROP EXTENSION IF EXISTS pg_stat_statements CASCADE;")
    # op.execute("DROP EXTENSION IF EXISTS pg_cron CASCADE;")
    # op.execute("DROP EXTENSION IF EXISTS btree_gist CASCADE;")
    return


__all__ = [
    "create_pg_stat_statements",
    "create_pg_cron",
    "create_btree_gist",
    "create_all_ext",
    "drop_all_ext",
]
