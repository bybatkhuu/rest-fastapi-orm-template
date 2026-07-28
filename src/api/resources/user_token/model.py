from datetime import datetime
from ipaddress import IPv4Address, IPv6Address

from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import INET

from api.database import BaseORM
from api.config import config


class UserTokenORM(BaseORM):
    kind: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # REFRESH, RESET, etc.
    token_hash: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text(
            "'ACTIVE'"
        ),  # ACTIVE, USED, EXPIRED, REVOKED, BLOCKED, etc.
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    used_ip: Mapped[IPv4Address | IPv6Address | None] = mapped_column(
        INET, nullable=True
    )
    family_token_id: Mapped[str | None] = mapped_column(
        String(64), index=True, nullable=True
    )  # Only for refresh tokens

    user_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(f"{config.db.prefix}user.id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "kind",
            "token_hash",
            name=f"uq__{config.db.prefix}user_token__user_id__kind__token_hash",
        ),
    )

    user = relationship("UserORM", foreign_keys=[user_id], back_populates="tokens")


__all__ = ["UserTokenORM"]
