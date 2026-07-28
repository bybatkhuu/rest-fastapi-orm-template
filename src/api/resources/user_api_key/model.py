from datetime import datetime
from ipaddress import (
    IPv4Address,
    IPv6Address,
    IPv4Network,
    IPv6Network,
    IPv4Interface,
    IPv6Interface,
)

from sqlalchemy import String, DateTime, ForeignKey, text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import INET, ARRAY

from api.database import BaseORM
from api.config import config


class UserApiKeyORM(BaseORM):
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    key_prefix: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    key_hash: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'ACTIVE'"),  # ACTIVE, DISABLED, EXPIRED, REVOKED, etc.
    )
    allowed_scopes: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        server_default=text("'{}'"),  # Empty means inherit all scopes from the user.
    )
    allowed_ips: Mapped[
        list[
            IPv4Address
            | IPv6Address
            | IPv4Network
            | IPv6Network
            | IPv4Interface
            | IPv6Interface
        ]
    ] = mapped_column(
        ARRAY(INET),
        nullable=False,
        server_default=text("'{}'"),  # Empty means allow from any IP.
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_used_ip: Mapped[IPv4Address | IPv6Address | None] = mapped_column(
        INET, nullable=True
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(f"{config.db.prefix}user.id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "key_prefix",
            "key_hash",
            name=f"uq__{config.db.prefix}user_api_key__key_prefix__key_hash",
        ),
    )

    user = relationship("UserORM", foreign_keys=[user_id], back_populates="api_keys")


__all__ = ["UserApiKeyORM"]
