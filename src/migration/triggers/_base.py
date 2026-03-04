from pydantic import validate_call
from alembic import op


@validate_call
def create_tr_generate_pk(table_names: list[str] | str) -> None:
    """Create trigger to generate primary key for table(s).

    Args:
        table_names (list[str] | str, required): List of table names or a table name.
    """

    if isinstance(table_names, str):
        table_names = [table_names]

    for _table_name in table_names:
        op.execute(
            f"""
            CREATE OR REPLACE TRIGGER tr__generate_pk__{_table_name}
            BEFORE INSERT ON "{_table_name}"
            FOR EACH ROW
            EXECUTE FUNCTION fn_tr__generate_pk();
            """
        )

    return


@validate_call
def create_tr_updated_at(table_names: list[str] | str) -> None:
    """Create trigger to update `updated_at` column for table(s).

    Args:
        table_names (list[str] | str, required): List of table names or a table name.
    """

    if isinstance(table_names, str):
        table_names = [table_names]

    for _table_name in table_names:
        op.execute(
            f"""
                CREATE OR REPLACE TRIGGER tr__updated_at__{_table_name}
                BEFORE UPDATE ON "{_table_name}"
                FOR EACH ROW
                EXECUTE PROCEDURE fn_tr__updated_at();
                """
        )

    return


@validate_call
def create_tr_stat_count(table_names: list[str] | str) -> None:
    """Create trigger to update stat count table for table(s).

    Args:
        table_names (list[str] | str, required): List of table names or a table name.
    """

    if isinstance(table_names, str):
        table_names = [table_names]

    for _table_name in table_names:
        op.execute(
            f"""
            CREATE OR REPLACE TRIGGER tr__update_stat_count__{_table_name}
            AFTER INSERT OR DELETE ON "{_table_name}"
            FOR EACH ROW
            EXECUTE FUNCTION fn_tr__update_stat_count();
            """
        )

        op.execute(
            f"""
            CREATE OR REPLACE TRIGGER tr__truncate_stat_count__{_table_name}
            AFTER TRUNCATE ON "{_table_name}"
            FOR EACH STATEMENT
            EXECUTE FUNCTION fn_tr__truncate_stat_count();
            """
        )

    return


__all__ = [
    "create_tr_generate_pk",
    "create_tr_updated_at",
    "create_tr_stat_count",
]
