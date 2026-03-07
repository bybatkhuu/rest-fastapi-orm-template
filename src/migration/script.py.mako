"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision}
Create Date: ${create_date}

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
${imports if imports else ""}
from alembic import context


# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    schema_upgrades()
    if context.get_x_argument(as_dictionary=True).get('data', None):
        data_upgrades()

    return


def downgrade() -> None:
    if context.get_x_argument(as_dictionary=True).get('data', None):
        data_downgrades()
    schema_downgrades()

    return


def schema_upgrades() -> None:
    """schema upgrade migrations go here."""
    ${upgrades if upgrades else "pass"}


def schema_downgrades() -> None:
    """schema downgrade migrations go here."""
    ${downgrades if downgrades else "pass"}


def data_upgrades() -> None:
    """Add any optional data upgrade migrations here!"""

    return


def data_downgrades() -> None:
    """Add any optional data downgrade migrations here!"""

    return
