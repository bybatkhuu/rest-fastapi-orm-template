from sqlalchemy import String, Boolean, text, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import BaseORM
from api.config import config


class RoleORM(BaseORM):
    name: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False  # admin, user, etc.
    )
    source: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'INTERNAL'"),  # INTERNAL, etc.
    )
    protected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=false()
    )
    description: Mapped[str] = mapped_column(
        String(256), nullable=False, server_default=text("''")
    )

    role_scopes = relationship(
        "RoleScopeORM", back_populates="role", passive_deletes=True
    )
    scopes = relationship(
        "ScopeORM",
        secondary=f"{config.db.prefix}role_scope",
        back_populates="roles",
        overlaps="role_scopes",
    )
    user_roles = relationship("UserRoleORM", back_populates="role")
    users = relationship(
        "UserORM",
        secondary=f"{config.db.prefix}user_role",
        back_populates="roles",
        overlaps="user_roles",
    )


__all__ = ["RoleORM"]
