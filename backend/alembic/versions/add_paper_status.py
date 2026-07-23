"""add status and error_message columns to papers

Revision ID: add_paper_status
Revises: initial
Create Date: 2026-07-27 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_paper_status"
down_revision: Union[str, None] = "initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "papers",
        sa.Column("status", sa.String(), nullable=False, server_default="processing"),
    )
    op.add_column(
        "papers",
        sa.Column("error_message", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("papers", "error_message")
    op.drop_column("papers", "status")
