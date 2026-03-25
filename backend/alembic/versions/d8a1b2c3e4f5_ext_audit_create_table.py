"""ext-audit: Create ext_audit_log table.

Revision ID: d8a1b2c3e4f5
Revises: c7f2e8a3d105
Create Date: 2026-03-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d8a1b2c3e4f5"
down_revision = "c7f2e8a3d105"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ext_audit_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("actor_email", sa.String(255), nullable=True),
        sa.Column("actor_role", sa.String(50), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("resource_name", sa.String(255), nullable=True),
        sa.Column("details", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", postgresql.INET, nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
    )
    op.create_index(
        "idx_ext_audit_log_timestamp",
        "ext_audit_log",
        [sa.text("timestamp DESC")],
    )
    op.create_index(
        "idx_ext_audit_log_actor", "ext_audit_log", ["actor_email"]
    )
    op.create_index(
        "idx_ext_audit_log_resource",
        "ext_audit_log",
        ["resource_type", "resource_id"],
    )
    op.create_index(
        "idx_ext_audit_log_action", "ext_audit_log", ["action"]
    )


def downgrade() -> None:
    op.drop_index("idx_ext_audit_log_action", table_name="ext_audit_log")
    op.drop_index("idx_ext_audit_log_resource", table_name="ext_audit_log")
    op.drop_index("idx_ext_audit_log_actor", table_name="ext_audit_log")
    op.drop_index("idx_ext_audit_log_timestamp", table_name="ext_audit_log")
    op.drop_table("ext_audit_log")
