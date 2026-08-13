import logging
import re
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import _get_session_factory
from app.services.embedder import _EMBED_MODEL, EMBEDDING_DIM, embed_query
from app.services.tracing import Tracer

logger = logging.getLogger(__name__)

_RRF_K = 60
_MAX_LEXICAL_TOKENS = 8

_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an",
    "and", "any", "are", "as", "at", "be", "because", "been", "before",
    "being", "below", "between", "both", "but", "by", "can", "cannot",
    "could", "did", "do", "does", "doing", "down", "during", "each", "few",
    "for", "from", "further", "get", "give", "had", "has", "have", "having",
    "he", "her", "here", "hers", "herself", "him", "himself", "his", "how",
    "i", "if", "in", "into", "is", "it", "its", "itself", "just", "me",
    "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off",
    "on", "once", "only", "or", "other", "our", "ours", "ourselves", "out",
    "over", "own", "paper", "paragraph", "please", "same", "say", "said",
    "she", "should", "so", "some", "such", "than", "that", "the", "their",
    "theirs", "them", "themselves", "then", "there", "these", "they", "this",
    "those", "through", "to", "too", "under", "until", "up", "us", "very",
    "was", "we", "were", "what", "when", "where", "which", "while", "who",
    "whom", "why", "will", "with", "would", "you", "your", "yours",
    "yourself", "yourselves",
}

_VECTOR_SELECT = """
    SELECT c.id, c.paper_id, c.metadata ->> 'section_heading' AS section_heading,
           c.content, c.parent_content, c.metadata, 1 - (c.embedding <=> CAST(:query_vec AS vector)) AS score
    FROM chunks c
    JOIN papers p ON p.id = c.paper_id
    WHERE p.status = 'ready'
      {filter_clause}
      AND 1 - (c.embedding <=> CAST(:query_vec AS vector)) >= :threshold
    ORDER BY score DESC
    LIMIT :top_k
"""

_LEXICAL_SELECT = """
    SELECT c.id, c.paper_id, c.metadata ->> 'section_heading' AS section_heading,
           c.content, c.parent_content, c.metadata,
           ts_rank_cd(to_tsvector('english', c.content), to_tsquery('english', :tsq), 32) AS score
    FROM chunks c
    JOIN papers p ON p.id = c.paper_id
    WHERE p.status = 'ready'
      {filter_clause}
      AND to_tsvector('english', c.content) @@ to_tsquery('english', :tsq)
    ORDER BY score DESC
    LIMIT :top_k
"""

_FILTER_CLAUSE = "AND c.paper_id::text = ANY(:paper_ids)"


@dataclass
class ChunkResult:
    chunk_id: str
    paper_id: str
    section_heading: str
    content: str
    score: float
    metadata: dict


def _content_tokens(query: str) -> list[str]:
    cleaned = re.sub(r"[^a-z0-9\s]+", " ", query.lower())
    tokens = [t for t in cleaned.split() if len(t) > 2 and t not in _STOPWORDS]
    return tokens[:_MAX_LEXICAL_TOKENS]


def _build_tsquery(query: str) -> str | None:
    tokens = _content_tokens(query)
    if len(tokens) < 2:
        return None
    return " | ".join(tokens)


def _rows_to_results(rows) -> list[ChunkResult]:
    results: list[ChunkResult] = []
    for row in rows:
        metadata = dict(row[5]) if row[5] else {}
        if row[4]:
            metadata["parent_content"] = row[4]
        results.append(
            ChunkResult(
                chunk_id=str(row[0]),
                paper_id=str(row[1]),
                section_heading=row[2] or "",
                content=row[3],
                score=float(row[6]) if row[6] is not None else 0.0,
                metadata=metadata,
            )
        )
    return results


def _rrf_fuse(
    vec_results: list[ChunkResult],
    lex_results: list[ChunkResult],
    top_k: int,
) -> list[ChunkResult]:
    vec_index = {c.chunk_id: rank for rank, c in enumerate(vec_results)}
    lex_index = {c.chunk_id: rank for rank, c in enumerate(lex_results)}

    rrf: dict[str, float] = {}
    for chunk_id, rank in vec_index.items():
        rrf[chunk_id] = 1.0 / (_RRF_K + rank + 1)
    for chunk_id, rank in lex_index.items():
        rrf[chunk_id] = rrf.get(chunk_id, 0.0) + 1.0 / (_RRF_K + rank + 1)

    by_chunk = {c.chunk_id: c for c in vec_results}
    for c in lex_results:
        if c.chunk_id not in by_chunk:
            by_chunk[c.chunk_id] = c

    fused: list[ChunkResult] = []
    for chunk_id, rrf_score in sorted(rrf.items(), key=lambda kv: kv[1], reverse=True):
        chunk = by_chunk[chunk_id]
        chunk.metadata["rrf_score"] = round(rrf_score, 6)
        if chunk_id not in vec_index:
            chunk.score = 0.0
        fused.append(chunk)
    return fused[:top_k]


async def retrieve(
    query: str,
    paper_ids: list[str] | None = None,
    top_k: int = 10,
    score_threshold: float | None = None,
    db: AsyncSession | None = None,
    tracer: Tracer | None = None,
) -> list[ChunkResult]:
    threshold = (
        settings.RAG_VECTOR_THRESHOLD
        if score_threshold is None
        else score_threshold
    )
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

    close_db = False
    if db is None:
        factory = _get_session_factory()
        db = factory()
        close_db = True

    try:
        vec_results: list[ChunkResult] = []
        if query_vec:
            vec_params: dict = {
                "query_vec": str(query_vec),
                "threshold": threshold,
                "top_k": top_k,
            }
            if paper_ids:
                vec_params["paper_ids"] = [str(pid) for pid in paper_ids]
            vec_stmt = text(
                _VECTOR_SELECT.format(filter_clause=_FILTER_CLAUSE if paper_ids else "")
            )
            if tracer:
                async with tracer.span(
                    "vector_search",
                    attributes={"top_k": top_k, "filter_paper_ids": bool(paper_ids), "threshold": threshold},
                ) as span:
                    rows = (await db.execute(vec_stmt, vec_params)).fetchall()
                    vec_results = _rows_to_results(rows)
                    span.attributes["results_count"] = len(vec_results)
                    span.attributes["empty_result"] = len(vec_results) == 0
                    span.attributes["retrieved_chunks"] = [
                        {
                            "chunk_id": c.chunk_id,
                            "paper_id": c.paper_id,
                            "section_heading": c.section_heading or "Unheaded Section",
                            "score": round(c.score, 4),
                            "snippet": c.content[:150],
                        }
                        for c in vec_results
                    ]
            else:
                rows = (await db.execute(vec_stmt, vec_params)).fetchall()
                vec_results = _rows_to_results(rows)
        elif tracer:
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

        lex_results: list[ChunkResult] = []
        tsq = _build_tsquery(query)
        if tsq:
            lex_params: dict = {"tsq": tsq, "top_k": top_k}
            if paper_ids:
                lex_params["paper_ids"] = [str(pid) for pid in paper_ids]
            lex_stmt = text(
                _LEXICAL_SELECT.format(filter_clause=_FILTER_CLAUSE if paper_ids else "")
            )
            if tracer:
                async with tracer.span(
                    "lexical_search",
                    attributes={"tsquery": tsq, "top_k": top_k, "filter_paper_ids": bool(paper_ids)},
                ) as span:
                    rows = (await db.execute(lex_stmt, lex_params)).fetchall()
                    lex_results = _rows_to_results(rows)
                    span.attributes["results_count"] = len(lex_results)
                    span.attributes["empty_result"] = len(lex_results) == 0
            else:
                rows = (await db.execute(lex_stmt, lex_params)).fetchall()
                lex_results = _rows_to_results(rows)

        if not vec_results and not lex_results:
            return []

        return _rrf_fuse(vec_results, lex_results, top_k)
    finally:
        if close_db:
            await db.close()
