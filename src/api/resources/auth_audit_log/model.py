from ipaddress import IPv4Address

from sqlalchemy import String, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import INET

from api.database import BaseORM
from api.config import config


class AuthAuditLogORM(BaseORM):
    auth_method: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # EMAIL_PASSWORD, VERIFY_TOKEN, REFRESH_TOKEN, RESET_TOKEN, ACCESS_TOKEN_PASSWORD, etc.
    route: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # /v1/auth/login, /v1/auth/token, etc.
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'PENDING'"),  # PENDING, SUCCESS, FAIL, REJECTED, etc.
    )
    actor_ip: Mapped[IPv4Address] = mapped_column(INET, nullable=False)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_agent: Mapped[str] = mapped_column(String(256), nullable=False)
    actor_type: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # GUEST, USER, API_KEY, WALLET, etc.

    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    secure_token_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey(f"{config.db.prefix}token.id", ondelete="SET NULL"),
        nullable=True,
    )

    secure_token = relationship(
        "TokenORM", foreign_keys=[secure_token_id], back_populates="auth_audit_logs"
    )


__all__ = ["AuthAuditLogORM"]
