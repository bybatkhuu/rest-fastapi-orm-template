from sqlalchemy import String, Boolean, text, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import BaseORM
from api.config import config


class ScopeORM(BaseORM):
    value: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False
    )  # all, me:read, roles:read, etc.
    protected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=false()
    )
    description: Mapped[str] = mapped_column(
        String(256), nullable=False, server_default=text("''")
    )

    role_scopes = relationship(
        "RoleScopeORM", back_populates="scope", passive_deletes=True
    )
    roles = relationship(
        "RoleORM",
        secondary=f"{config.db.prefix}role_scope",
        back_populates="scopes",
        overlaps="role_scopes",
    )


__all__ = ["ScopeORM"]
