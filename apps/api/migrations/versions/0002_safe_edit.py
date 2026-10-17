"""Short-lived proposal authority and durable uncertainty denial; no CAD history."""

import sqlalchemy as sa
from alembic import op

revision = "0002_safe_edit"
down_revision = "0001_authentication"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "write_records",
        sa.Column("id", sa.String(43), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("session_hash", sa.String(64), nullable=False),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
        sa.Column("purge_at", sa.BigInteger(), nullable=False),
    )
    for name in ("user_id", "session_hash", "expires_at", "purge_at"):
        op.create_index("ix_write_records_" + name, "write_records", [name])
    op.create_table(
        "write_fences",
        sa.Column("workspace_key", sa.String(64), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("record_id", sa.String(43), nullable=False, unique=True),
    )


def downgrade() -> None:
    raise RuntimeError("Destructive downgrade disabled; preserve unresolved fences")
