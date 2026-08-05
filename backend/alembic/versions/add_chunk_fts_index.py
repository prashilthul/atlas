from collections.abc import Sequence

from alembic import op

revision: str = "add_chunk_fts_index"
down_revision: str | None = "add_chat_message_trace_id"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX ix_chunks_content_fts ON chunks "
        "USING GIN (to_tsvector('english', content));"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chunks_content_fts;")
