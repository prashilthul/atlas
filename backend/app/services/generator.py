import logging
import re
from dataclasses import dataclass, field

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings
from app.services.retriever import ChunkResult

logger = logging.getLogger(__name__)

_BASE = settings.OPENROUTER_BASE_URL or "https://openrouter.ai/api/v1"

_SYSTEM_PROMPT = (
    "You are Paper Pilot, a research paper assistant. "
    "Answer the user's question based ONLY on the provided paper excerpts. "
    "Cite sources using [1], [2] markers corresponding to the provided chunks. "
    "If the context doesn't contain enough information to answer, "
    "say 'The provided paper excerpts do not contain information about this.'"
)

_MARKER_PATTERN = re.compile(r"\[(\d+)\]")


@dataclass
class Citation:
    chunk_id: str
    paper_id: str
    section_heading: str
    marker: str


@dataclass
class GenerationResult:
    answer: str
    citations: list[Citation] = field(default_factory=list)
    finish_reason: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0


def _build_context(chunks: list[ChunkResult]) -> str:
    lines = []
    for i, c in enumerate(chunks, start=1):
        heading = c.section_heading or "Untitled"
        lines.append(f"[{i}] (Section: {heading}) {c.content}")
    return "\n\n".join(lines)


def _extract_citations(
    answer: str, chunks: list[ChunkResult]
) -> list[Citation]:
    seen = set()
    citations = []
    for match in _MARKER_PATTERN.finditer(answer):
        n = int(match.group(1))
        if n < 1 or n > len(chunks):
            continue
        chunk = chunks[n - 1]
        key = (chunk.chunk_id, n)
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            Citation(
                chunk_id=chunk.chunk_id,
                paper_id=chunk.paper_id,
                section_heading=chunk.section_heading,
                marker=f"[{n}]",
            )
        )
    return citations


async def generate(
    query: str,
    chunks: list[ChunkResult],
    model: str = "openrouter/free",
    temperature: float = 0.1,
) -> GenerationResult:
    if not query or not chunks:
        return GenerationResult(
            answer="The provided paper excerpts do not contain information about this.",
            finish_reason="no_input",
        )

    context = _build_context(chunks)

    llm = ChatOpenAI(
        model=model,
        openai_api_key=settings.OPENROUTER_API_KEY,
        openai_api_base=_BASE,
        temperature=temperature,
        max_tokens=1024,
        streaming=False,
    )

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(
            content=f"Paper excerpts:\n\n{context}\n\n---\n\nQuestion: {query}"
        ),
    ]

    response = llm.invoke(messages)

    answer = response.content or ""
    citations = _extract_citations(answer, chunks)

    usage = response.usage_metadata if hasattr(response, "usage_metadata") else None
    input_tokens = usage.get("input_tokens", 0) if usage else 0
    output_tokens = usage.get("output_tokens", 0) if usage else 0

    return GenerationResult(
        answer=answer,
        citations=citations,
        finish_reason=response.response_metadata.get("finish_reason") if response.response_metadata else None,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
