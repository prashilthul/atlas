"""add trace_id column to chat_messages

Revision ID: add_chat_message_trace_id
Revises: add_span_id
Create Date: 2026-08-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_chat_message_trace_id"
down_revision: Union[str, None] = "add_span_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat_messages",
        sa.Column("trace_id", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_chat_messages_trace_id", "chat_messages", ["trace_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_chat_messages_trace_id", table_name="chat_messages")
    op.drop_column("chat_messages", "trace_id")
