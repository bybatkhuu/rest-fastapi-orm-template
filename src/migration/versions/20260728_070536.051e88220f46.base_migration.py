"""Base migration

Revision ID: 051e88220f46
Revises:
Create Date: 2026-07-28 07:05:36.696310+00:00

"""

from collections.abc import Sequence

from alembic import context

from migration import extensions
from migration import routines

# revision identifiers, used by Alembic.
revision: str = "051e88220f46"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    schema_upgrades()
    if context.get_x_argument(as_dictionary=True).get("data", None):
        data_upgrades()

    return


def downgrade() -> None:
    if context.get_x_argument(as_dictionary=True).get("data", None):
        data_downgrades()
    schema_downgrades()

    return


def schema_upgrades() -> None:
    """schema upgrade migrations go here."""

    # Extensions
    extensions.create_all_ext()

    # Functions and triggers
    routines.create_all_base_fn()
    return


def schema_downgrades() -> None:
    """schema downgrade migrations go here."""

    # Drop functions
    routines.drop_all_base_fn()

    # Drop extensions
    extensions.drop_all_ext()
    return


def data_upgrades() -> None:
    """Add any optional data upgrade migrations here!"""

    return


def data_downgrades() -> None:
    """Add any optional data downgrade migrations here!"""

    return
