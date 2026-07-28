from pydantic import validate_call
from sqlalchemy.sql import quoted_name
from alembic import op

# Generate primary key #
# def create_fn_tr_generate_pk() -> None:
#     """Create function to generate primary key for table."""

#     op.execute("""
#         CREATE OR REPLACE FUNCTION fn_tr__generate_pk()
#         RETURNS TRIGGER AS $BODY$
#         DECLARE
#             v_prefix VARCHAR(3);
#             v_current_ts VARCHAR;
#             v_gen_uuid VARCHAR;
#         BEGIN
#             IF NEW."id" IS NULL THEN
#                 v_current_ts := EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)::BIGINT::VARCHAR;
#                 v_gen_uuid := REPLACE(gen_random_uuid()::VARCHAR, '-', '');
#                 NEW."id" := v_current_ts || '_' || v_gen_uuid;
#             END IF;

#             RETURN NEW;
#         END;
#         $BODY$ LANGUAGE plpgsql;
#         """)
#     return


def create_fn_tr_generate_pk() -> None:
    """Create function to generate primary key for table."""

    op.execute("""
        CREATE OR REPLACE FUNCTION fn_tr__generate_pk()
        RETURNS TRIGGER AS $BODY$
        DECLARE
            v_prefix VARCHAR(3);
            v_current_ts VARCHAR;
            v_gen_uuid VARCHAR;
        BEGIN
            IF NEW."id" IS NULL THEN
                v_prefix := LOWER(SUBSTRING(TG_TABLE_NAME FROM 4 FOR 3));
                v_current_ts := EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)::BIGINT::VARCHAR;
                v_gen_uuid := REPLACE(gen_random_uuid()::VARCHAR, '-', '');
                NEW."id" := v_prefix || v_current_ts || '_' || v_gen_uuid;
            END IF;

            RETURN NEW;
        END;
        $BODY$ LANGUAGE plpgsql;
        """)
    return


@validate_call
def create_tr_generate_pk(table_names: list[str] | str) -> None:
    """Create trigger to generate primary key for table(s).

    Args:
        table_names (list[str] | str, required): List of table names or a table name.
    """

    if isinstance(table_names, str):
        table_names = [table_names]

    for _table_name in table_names:
        _safe_table_name = quoted_name(_table_name, quote=True)
        op.execute(f"""
            CREATE OR REPLACE TRIGGER tr__{_safe_table_name}__generate_pk
            BEFORE INSERT ON "{_safe_table_name}"
            FOR EACH ROW
            EXECUTE FUNCTION fn_tr__generate_pk();
            """)

    return


# Generate primary key #


# Update `updated_at` column #
def create_fn_tr_updated_at() -> None:
    """Create function to update `updated_at` column."""

    op.execute("""
        CREATE OR REPLACE FUNCTION fn_tr__updated_at()
        RETURNS TRIGGER AS $BODY$
        BEGIN
            NEW."updated_at" = CURRENT_TIMESTAMP;

            RETURN NEW;
        END;
        $BODY$ LANGUAGE plpgsql;
        """)
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
        _safe_table_name = quoted_name(_table_name, quote=True)

        op.execute(f"""
            CREATE OR REPLACE TRIGGER tr__{_safe_table_name}__updated_at
            BEFORE UPDATE ON "{_safe_table_name}"
            FOR EACH ROW
            EXECUTE PROCEDURE fn_tr__updated_at();
            """)

    return


# Update `updated_at` column


# Update stat count #
def create_fn_tr_stat_count() -> None:
    """Create function to update stat count for `fot_table_stat` table."""

    op.execute("""
        CREATE OR REPLACE FUNCTION fn_tr__update_stat_count()
        RETURNS TRIGGER AS $BODY$
        BEGIN
            IF (TG_OP = 'INSERT') THEN
                INSERT INTO "fot_table_stat" ("table_name", "insert_count", "row_count")
                VALUES (TG_TABLE_NAME, 1, 1)
                ON CONFLICT ("table_name") DO UPDATE
                SET "insert_count" = "fot_table_stat"."insert_count" + 1,
                    "row_count" = "fot_table_stat"."row_count" + 1;
            ELSIF (TG_OP = 'DELETE') THEN
                UPDATE "fot_table_stat"
                SET "delete_count" = "delete_count" + 1, "row_count" = "row_count" - 1
                WHERE "table_name" = TG_TABLE_NAME;
            END IF;

            RETURN NULL;
        END;
        $BODY$ LANGUAGE plpgsql;
        """)

    op.execute("""
        CREATE OR REPLACE FUNCTION fn_tr__truncate_stat_count()
        RETURNS TRIGGER AS $BODY$
        BEGIN
            UPDATE "fot_table_stat"
            SET "insert_count" = 0, "delete_count" = 0, "row_count" = 0
            WHERE "table_name" = TG_TABLE_NAME;

            RETURN NULL;
        END;
        $BODY$ LANGUAGE plpgsql;
        """)
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
        _safe_table_name = quoted_name(_table_name, quote=True)
        op.execute(f"""
            CREATE OR REPLACE TRIGGER tr__{_safe_table_name}__update_stat_count
            AFTER INSERT OR DELETE ON "{_safe_table_name}"
            FOR EACH ROW
            EXECUTE FUNCTION fn_tr__update_stat_count();
            """)

        op.execute(f"""
            CREATE OR REPLACE TRIGGER tr__{_safe_table_name}__truncate_stat_count
            AFTER TRUNCATE ON "{_safe_table_name}"
            FOR EACH STATEMENT
            EXECUTE FUNCTION fn_tr__truncate_stat_count();
            """)

    return


# Update stat count #


def create_all_base_fn() -> None:
    """Create all base functions."""

    create_fn_tr_generate_pk()
    create_fn_tr_updated_at()
    create_fn_tr_stat_count()
    return


@validate_call
def create_all_base_tr(table_names: list[str] | str) -> None:
    """Create all base triggers for table(s)."""

    create_tr_generate_pk(table_names=table_names)
    create_tr_updated_at(table_names=table_names)
    create_tr_stat_count(table_names=table_names)
    return


def drop_all_base_fn() -> None:
    """Drop all base functions."""

    op.execute("DROP FUNCTION IF EXISTS fn_tr__truncate_stat_count() CASCADE;")
    op.execute("DROP FUNCTION IF EXISTS fn_tr__update_stat_count() CASCADE;")
    op.execute("DROP FUNCTION IF EXISTS fn_tr__updated_at() CASCADE;")
    op.execute("DROP FUNCTION IF EXISTS fn_tr__generate_pk() CASCADE;")
    return


__all__ = [
    "create_fn_tr_generate_pk",
    "create_tr_generate_pk",
    "create_fn_tr_updated_at",
    "create_tr_updated_at",
    "create_fn_tr_stat_count",
    "create_tr_stat_count",
    "create_all_base_fn",
    "create_all_base_tr",
    "drop_all_base_fn",
]
