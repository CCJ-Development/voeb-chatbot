"""ext_token: Create ext_token_usage and ext_token_user_limit tables

Revision ID: b3e4a7d91f08
Revises: ff7273065d0d
Create Date: 2026-03-09 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "b3e4a7d91f08"
down_revision = "ff7273065d0d"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    # --- ext_token_usage ---
    op.create_table(
        "ext_token_usage",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("model_name", sa.String(255), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "completion_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_ext_token_usage_user_id", "ext_token_usage", ["user_id"]
    )
    op.create_index(
        "idx_ext_token_usage_model", "ext_token_usage", ["model_name"]
    )
    op.create_index(
        "idx_ext_token_usage_created_at", "ext_token_usage", ["created_at"]
    )
    op.create_index(
        "idx_ext_token_usage_user_time", "ext_token_usage", ["user_id", "created_at"]
    )

    # --- ext_token_user_limit ---
    op.create_table(
        "ext_token_user_limit",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_budget", sa.Integer(), nullable=False),
        sa.Column("period_hours", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("user_id", name="uq_ext_token_user_limit_user_id"),
        sa.CheckConstraint("token_budget > 0", name="ck_ext_token_budget_positive"),
        sa.CheckConstraint("period_hours > 0", name="ck_ext_token_period_positive"),
    )


def downgrade() -> None:
    op.drop_table("ext_token_user_limit")
    op.drop_table("ext_token_usage")
