from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import _get_session_factory
from app.services.embedder import embed_query


@dataclass
class ChunkResult:
    chunk_id: str
    paper_id: str
    section_heading: str
    content: str
    score: float
    metadata: dict


async def retrieve(
    query: str,
    paper_ids: list[str] | None = None,
    top_k: int = 10,
    score_threshold: float = 0.4,
    db: AsyncSession | None = None,
) -> list[ChunkResult]:
    query_vec = embed_query(query)
    if not query_vec:
        return []

    close_db = False
    if db is None:
        factory = _get_session_factory()
        db = factory()
        close_db = True

    try:
        params: dict = {
            "query_vec": query_vec,
            "threshold": score_threshold,
            "top_k": top_k,
        }

        if paper_ids:
            stmt = text("""
                SELECT c.id, c.paper_id, c.meta_data ->> 'section_heading' as section_heading,
                       c.content, c.meta_data, 1 - (c.embedding <=> :query_vec) AS score
                FROM chunks c
                WHERE c.paper_id = ANY(:paper_ids)
                  AND 1 - (c.embedding <=> :query_vec) >= :threshold
                ORDER BY score DESC
                LIMIT :top_k
            """)
            params["paper_ids"] = [UUID(pid) for pid in paper_ids]
        else:
            stmt = text("""
                SELECT c.id, c.paper_id, c.meta_data ->> 'section_heading' as section_heading,
                       c.content, c.meta_data, 1 - (c.embedding <=> :query_vec) AS score
                FROM chunks c
                WHERE 1 - (c.embedding <=> :query_vec) >= :threshold
                ORDER BY score DESC
                LIMIT :top_k
            """)

        result = await db.execute(stmt, params)
        rows = result.fetchall()

        return [
            ChunkResult(
                chunk_id=str(row[0]),
                paper_id=str(row[1]),
                section_heading=row[2] or "",
                content=row[3],
                score=float(row[5]),
                metadata=dict(row[4]) if row[4] else {},
            )
            for row in rows
        ]
    finally:
        if close_db:
            await db.close()