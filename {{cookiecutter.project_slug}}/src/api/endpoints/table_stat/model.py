from sqlalchemy import String, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from api.core.models import BaseORM


class TableStatORM(BaseORM):
    table_name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    insert_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    delete_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    row_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )


__all__ = ["TableStatORM"]
