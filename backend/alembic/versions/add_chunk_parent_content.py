from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "add_chunk_parent_content"
down_revision: str | None = "add_chunk_fts_index"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("chunks", sa.Column("parent_content", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("chunks", "parent_content")
