"""add otp table

Revision ID: 20240814_0002
Revises: 20240814_0001
Create Date: 2024-08-14 01:00:00.000000
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "20240814_0002"
down_revision = "20240814_0001"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "otps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(length=12), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_otps_code", "otps", ["code"], unique=False)
    op.create_index("ix_otps_consumed", "otps", ["consumed"], unique=False)
    op.create_index("ix_otps_expires_at", "otps", ["expires_at"], unique=False)
    op.create_index("ix_otps_user_id", "otps", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_table("otps")
