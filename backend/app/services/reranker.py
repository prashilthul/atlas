import logging

import httpx

from app.config import settings
from app.services.retriever import ChunkResult
from app.services.tracing import Tracer

logger = logging.getLogger(__name__)

_BASE = settings.OPENROUTER_BASE_URL or "https://openrouter.ai/api/v1"


async def rerank(
    query: str,
    chunks: list[ChunkResult],
    top_k: int = 5,
    tracer: Tracer | None = None,
) -> list[ChunkResult]:
    if not chunks or not query:
        if tracer:
            async with tracer.span(
                "rerank",
                attributes={"model": "nvidia/llama-nemotron-rerank-vl-1b-v2:free", "input_count": 0, "output_count": 0},
            ):
                pass
        return chunks[:top_k]

    input_count = len(chunks)

    if tracer:
        async with tracer.span(
            "rerank",
            attributes={"model": "nvidia/llama-nemotron-rerank-vl-1b-v2:free", "input_count": input_count},
        ) as span:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(
                        f"{_BASE}/rerank",
                        headers={
                            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": "nvidia/llama-nemotron-rerank-vl-1b-v2:free",
                            "query": query,
                            "documents": [c.content for c in chunks],
                            "top_n": top_k,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()

                results = data.get("results")
                if not results:
                    span.attributes["output_count"] = 0
                    return chunks[:top_k]

                index_to_chunk = {i: c for i, c in enumerate(chunks)}
                reranked: list[ChunkResult] = []
                for r in sorted(results, key=lambda x: x.get("relevance_score", 0), reverse=True):
                    idx = r.get("index")
                    if idx is not None and idx in index_to_chunk:
                        reranked.append(index_to_chunk[idx])

                output = reranked[:top_k]
                span.attributes["output_count"] = len(output)
                return output
            except Exception:
                logger.warning("reranker unavailable, falling back to vector search order")
                span.attributes["output_count"] = 0
                return chunks[:top_k]
    else:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{_BASE}/rerank",
                    headers={
                        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "nvidia/llama-nemotron-rerank-vl-1b-v2:free",
                        "query": query,
                        "documents": [c.content for c in chunks],
                        "top_n": top_k,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            results = data.get("results")
            if not results:
                return chunks[:top_k]

            index_to_chunk = {i: c for i, c in enumerate(chunks)}
            reranked: list[ChunkResult] = []
            for r in sorted(results, key=lambda x: x.get("relevance_score", 0), reverse=True):
                idx = r.get("index")
                if idx is not None and idx in index_to_chunk:
                    reranked.append(index_to_chunk[idx])

            return reranked[:top_k]
        except Exception:
            logger.warning("reranker unavailable, falling back to vector search order")
            return chunks[:top_k]
