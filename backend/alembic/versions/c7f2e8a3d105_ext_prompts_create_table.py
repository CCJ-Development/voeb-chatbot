"""ext_prompts: Create ext_custom_prompts table

Revision ID: c7f2e8a3d105
Revises: b3e4a7d91f08
Create Date: 2026-03-09 14:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c7f2e8a3d105"
down_revision = "b3e4a7d91f08"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    op.create_table(
        "ext_custom_prompts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column(
            "category", sa.String(50), nullable=False, server_default="general"
        ),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
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
    )
    op.create_index(
        "idx_ext_custom_prompts_active_priority",
        "ext_custom_prompts",
        ["is_active", "priority"],
    )


def downgrade() -> None:
    op.drop_table("ext_custom_prompts")
