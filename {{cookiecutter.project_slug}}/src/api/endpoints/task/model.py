from sqlalchemy import String, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from api.core.models import BaseORM


class TaskORM(BaseORM):
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    point: Mapped[int] = mapped_column(
        Integer, nullable=False, default=70, server_default=text("70")
    )


__all__ = ["TaskORM"]
