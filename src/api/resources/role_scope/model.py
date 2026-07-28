from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import BaseORM
from api.config import config


class RoleScopeORM(BaseORM):
    role_name: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(
            f"{config.db.prefix}role.name", onupdate="CASCADE", ondelete="CASCADE"
        ),
        nullable=False,
    )
    scope_value: Mapped[str] = mapped_column(
        String(128),
        ForeignKey(
            f"{config.db.prefix}scope.value", onupdate="CASCADE", ondelete="CASCADE"
        ),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "role_name",
            "scope_value",
            name=f"uq__{config.db.prefix}role_scope__role_name__scope_value",
        ),
    )

    role = relationship(
        "RoleORM",
        foreign_keys=[role_name],
        back_populates="role_scopes",
        overlaps="roles,scopes",
    )
    scope = relationship(
        "ScopeORM",
        foreign_keys=[scope_value],
        back_populates="role_scopes",
        overlaps="roles,scopes",
    )


__all__ = ["RoleScopeORM"]
