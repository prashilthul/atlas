import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import _get_session_factory
from app.services.embedder import EMBEDDING_DIM, _EMBED_MODEL, embed_query
from app.services.tracing import Tracer

logger = logging.getLogger(__name__)


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
    score_threshold: float = 0.0,
    db: AsyncSession | None = None,
    tracer: Tracer | None = None,
) -> list[ChunkResult]:
    query_vec: list[float] = []
    embed_error: str | None = None
    try:
        if tracer:
            async with tracer.span(
                "embed", attributes={"model": _EMBED_MODEL, "input_length": len(query), "dimension": EMBEDDING_DIM}
            ) as span:
                query_vec = embed_query(query)
                span.attributes["dimension"] = len(query_vec) if query_vec else 0
        else:
            query_vec = embed_query(query)
    except Exception as exc:
        embed_error = str(exc)
        logger.error("Query embedding failed: %s", exc)

    if not query_vec:
        if tracer:
            async with tracer.span(
                "vector_search",
                attributes={
                    "top_k": top_k,
                    "results_count": 0,
                    "empty_result": True,
                    "filter_paper_ids": bool(paper_ids),
                    "embed_error": embed_error or "empty_query",
                },
            ):
                pass
        return []

    close_db = False
    if db is None:
        factory = _get_session_factory()
        db = factory()
        close_db = True

    try:
        params: dict = {
            "query_vec": str(query_vec),
            "threshold": score_threshold,
            "top_k": top_k,
        }

        if paper_ids:
            stmt = text("""
                SELECT c.id, c.paper_id, c.metadata ->> 'section_heading' as section_heading,
                       c.content, c.metadata, 1 - (c.embedding <=> CAST(:query_vec AS vector)) AS score
                FROM chunks c
                JOIN papers p ON p.id = c.paper_id
                WHERE p.status = 'ready'
                  AND c.paper_id::text = ANY(:paper_ids)
                  AND 1 - (c.embedding <=> CAST(:query_vec AS vector)) >= :threshold
                ORDER BY score DESC
                LIMIT :top_k
            """)
            params["paper_ids"] = [str(pid) for pid in paper_ids]
        else:
            stmt = text("""
                SELECT c.id, c.paper_id, c.metadata ->> 'section_heading' as section_heading,
                       c.content, c.metadata, 1 - (c.embedding <=> CAST(:query_vec AS vector)) AS score
                FROM chunks c
                JOIN papers p ON p.id = c.paper_id
                WHERE p.status = 'ready'
                  AND 1 - (c.embedding <=> CAST(:query_vec AS vector)) >= :threshold
                ORDER BY score DESC
                LIMIT :top_k
            """)

        if tracer:
            async with tracer.span(
                "vector_search",
                attributes={"top_k": top_k, "filter_paper_ids": bool(paper_ids)},
            ) as span:
                result = await db.execute(stmt, params)
                rows = result.fetchall()
                span.attributes["results_count"] = len(rows)
                span.attributes["empty_result"] = len(rows) == 0
                span.attributes["retrieved_chunks"] = [
                    {
                        "chunk_id": str(r[0]),
                        "paper_id": str(r[1]),
                        "section_heading": r[2] or "Unheaded Section",
                        "score": round(float(r[5]), 4),
                        "snippet": (r[3] or "")[:150],
                    }
                    for r in rows
                ]
        else:
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