from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import BaseORM
from api.config import config


class UserRoleORM(BaseORM):
    user_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(
            f"{config.db.prefix}user.id", onupdate="CASCADE", ondelete="CASCADE"
        ),
        nullable=False,
    )
    role_name: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(
            f"{config.db.prefix}role.name", onupdate="CASCADE", ondelete="RESTRICT"
        ),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "role_name",
            name=f"uq__{config.db.prefix}user_role__user_id__role_name",
        ),
    )

    user = relationship(
        "UserORM",
        foreign_keys=[user_id],
        back_populates="user_roles",
        overlaps="users,roles",
    )
    role = relationship(
        "RoleORM",
        foreign_keys=[role_name],
        back_populates="user_roles",
        overlaps="users,roles",
    )


__all__ = ["UserRoleORM"]
