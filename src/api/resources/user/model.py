from datetime import datetime
from ipaddress import IPv4Address, IPv6Address
from typing import Any, TYPE_CHECKING

from sqlalchemy import String, DateTime, Text, Boolean, text, false
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.dialects.postgresql import JSONB, INET

from api.database import BaseORM

if TYPE_CHECKING:
    from api.resources.role.model import RoleORM
    from api.resources.scope.model import ScopeORM

from api.config import config


class UserORM(BaseORM):
    nickname: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'PENDING'"),  # PENDING, ACTIVE, DISABLED, DELETED, etc.
    )
    timezone: Mapped[str] = mapped_column(  # UTC, Asia/Seoul, Australia/Sydney, etc
        String(32), nullable=False, server_default=text("'UTC'")
    )
    protected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=false()
    )
    last_login_ip: Mapped[IPv4Address | IPv6Address | None] = mapped_column(
        INET, nullable=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict[str, Any] | None] = mapped_column(
        MutableDict.as_mutable(JSONB), nullable=True
    )

    user_roles = relationship(
        "UserRoleORM", back_populates="user", passive_deletes=True
    )
    roles = relationship(
        "RoleORM",
        secondary=f"{config.db.prefix}user_role",
        back_populates="users",
        overlaps="user_roles",
    )
    tokens = relationship("UserTokenORM", back_populates="user", passive_deletes=True)
    api_keys = relationship(
        "UserApiKeyORM", back_populates="user", passive_deletes=True
    )

    async def async_get_permissions(self) -> tuple[set[str], set[str]]:
        """Get the roles and scopes of the user."""

        _role_orms: list[RoleORM] = await self.awaitable_attrs.roles
        _roles: set[str] = set()
        _scopes: set[str] = set()
        for _role_orm in _role_orms:
            _roles.add(_role_orm.name)
            _scope_orms: list[ScopeORM] = await _role_orm.awaitable_attrs.scopes
            for _scope_orm in _scope_orms:
                _scopes.add(_scope_orm.value)

        return _roles, _scopes


__all__ = ["UserORM"]
