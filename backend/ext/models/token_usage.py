"""SQLAlchemy models for ext-token (LLM Usage Tracking + Token Limits).

Two tables:
- ext_token_usage: Granular log of every LLM call (user, model, tokens, timestamp)
- ext_token_user_limit: Per-user token budgets with rolling time windows
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean
from sqlalchemy import CheckConstraint
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from onyx.db.models import Base


class ExtTokenUsage(Base):
    __tablename__ = "ext_token_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_ext_token_usage_user_id", "user_id"),
        Index("idx_ext_token_usage_model", "model_name"),
        Index("idx_ext_token_usage_created_at", "created_at"),
        Index("idx_ext_token_usage_user_time", "user_id", "created_at"),
    )


class ExtTokenUserLimit(Base):
    __tablename__ = "ext_token_user_limit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_budget: Mapped[int] = mapped_column(Integer, nullable=False)
    period_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_ext_token_user_limit_user_id"),
        CheckConstraint("token_budget > 0", name="ck_ext_token_budget_positive"),
        CheckConstraint("period_hours > 0", name="ck_ext_token_period_positive"),
    )
