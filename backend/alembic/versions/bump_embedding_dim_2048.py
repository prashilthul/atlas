from collections.abc import Sequence

from alembic import op

revision: str = "bump_embedding_dim_2048"
down_revision: str | None = "add_chunk_parent_content"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_chunks_embedding")
    op.execute("ALTER TABLE chunks ALTER COLUMN embedding DROP NOT NULL")
    op.execute("UPDATE chunks SET embedding = NULL")
    op.execute(
        "ALTER TABLE chunks ALTER COLUMN embedding TYPE vector(2048) "
        "USING embedding::vector(2048)"
    )


def downgrade() -> None:
    op.execute("UPDATE chunks SET embedding = NULL")
    op.execute(
        "ALTER TABLE chunks ALTER COLUMN embedding TYPE vector(768) "
        "USING embedding::vector(768)"
    )
    op.execute(
        "CREATE INDEX idx_chunks_embedding "
        "ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10)"
    )
