"""add span_id column to trace_spans

Revision ID: add_span_id
Revises: initial
Create Date: 2026-07-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_span_id"
down_revision: Union[str, None] = "initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "trace_spans",
        sa.Column("span_id", sa.String(), nullable=False, server_default=""),
    )
    op.create_unique_constraint("uq_trace_spans_span_id", "trace_spans", ["span_id"])


def downgrade() -> None:
    op.drop_constraint("uq_trace_spans_span_id", "trace_spans", type_="unique")
    op.drop_column("trace_spans", "span_id")
