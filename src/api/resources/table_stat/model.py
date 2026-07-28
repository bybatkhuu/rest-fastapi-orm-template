from sqlalchemy import String, BigInteger, text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from api.database import BaseORM


class TableStatORM(BaseORM):
    table_name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    insert_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    delete_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    row_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )

    __table_args__ = (
        CheckConstraint("0 <= insert_count", name="insert_count__non_negative"),
        CheckConstraint("0 <= delete_count", name="delete_count__non_negative"),
        CheckConstraint("0 <= row_count", name="row_count__non_negative"),
    )


__all__ = ["TableStatORM"]
