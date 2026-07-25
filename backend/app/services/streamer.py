import json
import logging
import uuid
from collections.abc import AsyncGenerator

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import settings
from app.services.generator import _SYSTEM_PROMPT, _build_context, _extract_citations
from app.services.retriever import ChunkResult

logger = logging.getLogger(__name__)

_BASE = settings.OPENROUTER_BASE_URL or "https://openrouter.ai/api/v1"


async def stream_generate(
    query: str,
    chunks: list[ChunkResult],
    model: str = "openrouter/free",
    temperature: float = 0.1,
) -> AsyncGenerator[str, None]:
    trace_id = str(uuid.uuid4())

    if not query or not chunks:
        yield f"event: done\ndata: {json.dumps({'citations': [], 'trace_id': trace_id})}\n\n"
        return

    context = _build_context(chunks)

    llm = ChatOpenAI(
        model=model,
        openai_api_key=settings.OPENROUTER_API_KEY,
        openai_api_base=_BASE,
        temperature=temperature,
        max_tokens=1024,
        streaming=True,
    )

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(
            content=f"Paper excerpts:\n\n{context}\n\n---\n\nQuestion: {query}"
        ),
    ]

    full_text = ""

    try:
        async for chunk in llm.astream(messages):
            token = chunk.content or ""
            if token:
                full_text += token
                yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"

        citations = _extract_citations(full_text, chunks)
        yield f"event: done\ndata: {json.dumps({'citations': [c.__dict__ for c in citations], 'trace_id': trace_id})}\n\n"

    except Exception as e:
        logger.warning("stream generation failed: %s", e)
        yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
