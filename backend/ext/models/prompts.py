"""SQLAlchemy model for ext-prompts (Custom System Prompts).

Single table: ext_custom_prompts — stores global system prompt fragments
that get prepended to every LLM call.
"""

from datetime import datetime

from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import func
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from onyx.db.models import Base


class ExtCustomPrompt(Base):
    __tablename__ = "ext_custom_prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="general"
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default="100")
    is_active: Mapped[bool] = mapped_column(
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
        Index(
            "idx_ext_custom_prompts_active_priority",
            "is_active",
            "priority",
        ),
    )
