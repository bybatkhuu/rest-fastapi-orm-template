from pydantic import validate_call
from alembic import op


def create_fn_generate_pk() -> None:
    """Create function to generate primary key for table."""

    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_tr__generate_pk()
        RETURNS TRIGGER AS $BODY$
        DECLARE
            v_prefix VARCHAR(3);
            v_current_ts VARCHAR;
            v_gen_uuid VARCHAR;
        BEGIN
            IF NEW."id" IS NULL THEN
                v_prefix := LOWER(SUBSTRING(TG_TABLE_NAME FROM 5 FOR 3));
                v_current_ts := EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)::BIGINT::VARCHAR;
                v_gen_uuid := REPLACE(gen_random_uuid()::VARCHAR, '-', '');
                NEW."id" := v_prefix || v_current_ts || '_' || v_gen_uuid;
            END IF;

            RETURN NEW;
        END;
        $BODY$ LANGUAGE plpgsql;
        """
    )

    return


def create_fn_updated_at() -> None:
    """Create function to update `updated_at` column."""

    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_tr__updated_at()
        RETURNS TRIGGER AS $BODY$
        BEGIN
            NEW."updated_at" = CURRENT_TIMESTAMP;

            RETURN NEW;
        END;
        $BODY$ LANGUAGE plpgsql;
        """
    )

    return


@validate_call
def create_fn_stat_count(table_name: str) -> None:
    """Create function to update stat count for stat table.

    Args:
        table_name (str, required): Name of the stat table.
    """

    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION fn_tr__update_stat_count()
        RETURNS TRIGGER AS $BODY$
        BEGIN
            IF (TG_OP = 'INSERT') THEN
                INSERT INTO "{table_name}" ("table_name", "insert_count", "row_count")
                VALUES (TG_TABLE_NAME, 1, 1)
                ON CONFLICT ("table_name") DO UPDATE
                SET "insert_count" = "{table_name}"."insert_count" + 1,
                    "row_count" = "{table_name}"."row_count" + 1;
            ELSIF (TG_OP = 'DELETE') THEN
                UPDATE "{table_name}"
                SET "delete_count" = "delete_count" + 1, "row_count" = "row_count" - 1
                WHERE "table_name" = TG_TABLE_NAME;
            END IF;

            RETURN NULL;
        END;
        $BODY$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION fn_tr__truncate_stat_count()
        RETURNS TRIGGER AS $BODY$
        BEGIN
            UPDATE "{table_name}"
            SET "insert_count" = 0, "delete_count" = 0, "row_count" = 0
            WHERE "table_name" = TG_TABLE_NAME;

            RETURN NULL;
        END;
        $BODY$ LANGUAGE plpgsql;
        """
    )

    return


def drop_fn_all() -> None:
    """Drop function to generate primary key for table."""

    op.execute("DROP FUNCTION IF EXISTS fn_tr__truncate_stat_count() CASCADE;")
    op.execute("DROP FUNCTION IF EXISTS fn_tr__update_stat_count() CASCADE;")
    op.execute("DROP FUNCTION IF EXISTS fn_tr__updated_at() CASCADE;")
    op.execute("DROP FUNCTION IF EXISTS fn_tr__generate_pk() CASCADE;")

    return


__all__ = [
    "create_fn_generate_pk",
    "create_fn_updated_at",
    "create_fn_stat_count",
    "drop_fn_all",
]
