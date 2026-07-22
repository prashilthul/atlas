import re
from dataclasses import dataclass

import tiktoken

from app.schemas import SectionSchema

_ENCODING = tiktoken.get_encoding("cl100k_base")
_MAX_TOKENS = 512
_OVERLAP_TOKENS = 64

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass
class ChunkData:
    paper_id: str
    section_heading: str
    section_level: int
    content: str
    chunk_index: int
    total_sections: int


def _num_tokens(text: str) -> int:
    return len(_ENCODING.encode(text))


def _chunk_section_content(
    content: str,
    heading: str,
    section_level: int,
    paper_id: str,
    total_sections: int,
    chunk_start_index: int,
) -> list[ChunkData]:
    """Split section into chunks with overlap. Empty content still produces one chunk with heading only."""
    heading_tokens = _num_tokens(heading)

    # Single chunk if under limit
    text_for_counting = f"{heading}\n{content}" if content else heading
    if _num_tokens(text_for_counting) <= _MAX_TOKENS:
        return [
            ChunkData(
                paper_id=paper_id,
                section_heading=heading,
                section_level=section_level,
                content=text_for_counting,
                chunk_index=chunk_start_index,
                total_sections=total_sections,
            )
        ]

    sentences = _SENTENCE_SPLIT.split(content)
    if not sentences:
        return [
            ChunkData(
                paper_id=paper_id,
                section_heading=heading,
                section_level=section_level,
                content=heading,
                chunk_index=chunk_start_index,
                total_sections=total_sections,
            )
        ]

    chunks: list[ChunkData] = []
    overlap_sentences: list[str] = []
    sent_idx = 0

    while sent_idx < len(sentences):
        chunk_sentences: list[str] = list(overlap_sentences)
        tokens = heading_tokens + sum(_num_tokens(s) for s in chunk_sentences)

        # Add sentences until token limit
        while sent_idx < len(sentences):
            s_tokens = _num_tokens(sentences[sent_idx])
            if tokens + s_tokens > _MAX_TOKENS:
                break
            chunk_sentences.append(sentences[sent_idx])
            tokens += s_tokens
            sent_idx += 1

        chunk_text = f"{heading}\n{' '.join(chunk_sentences)}"

        chunks.append(
            ChunkData(
                paper_id=paper_id,
                section_heading=heading,
                section_level=section_level,
                content=chunk_text,
                chunk_index=chunk_start_index + len(chunks),
                total_sections=total_sections,
            )
        )

        # Compute overlap from tail of this chunk's sentences
        overlap_sentences = []
        overlap_tokens = 0
        for s in reversed(chunk_sentences):
            s_t = _num_tokens(s)
            if overlap_tokens + s_t > _OVERLAP_TOKENS:
                break
            overlap_sentences.insert(0, s)
            overlap_tokens += s_t

    return chunks


def chunk_sections(sections: list[SectionSchema], paper_id: str) -> list[ChunkData]:
    total = len(sections)
    all_chunks: list[ChunkData] = []

    for section in sections:
        section_chunks = _chunk_section_content(
            content=section.content,
            heading=section.heading,
            section_level=section.level,
            paper_id=paper_id,
            total_sections=total,
            chunk_start_index=len(all_chunks),
        )
        all_chunks.extend(section_chunks)

    return all_chunks
