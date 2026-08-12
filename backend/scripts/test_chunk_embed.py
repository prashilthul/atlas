import sys
from pathlib import Path

import tiktoken

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.chunker import chunk_sections
from app.services.parser import parse_pdf

PDF_PATH = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "arxiv-sample.pdf"
_ENCODING = tiktoken.get_encoding("cl100k_base")


def main() -> None:
    print("=" * 60)
    print("Paper Pilot - Chunk & Embed Test")
    print("=" * 60)

    print("\n--- Parsing PDF ---")
    paper = parse_pdf(str(PDF_PATH))
    print(f"  Title: {paper.title}")
    print(f"  Sections: {len(paper.sections)}")
    for s in paper.sections:
        t = len(_ENCODING.encode(s.content))
        print(f"    [{s.level}] {s.heading} ({t} tokens)")

    print("\n--- Chunking ---")
    chunks = chunk_sections(paper.sections, paper_id="test-001")
    print(f"  Total chunks: {len(chunks)}")
    for i, c in enumerate(chunks):
        tk = _ENCODING.encode(c.content)
        print(f"  [{i}] level={c.section_level} tokens={len(tk)} heading={c.section_heading[:50]}")

    print("\n--- Token distribution ---")
    token_counts = [len(_ENCODING.encode(c.content)) for c in chunks]
    if token_counts:
        print(f"  Min: {min(token_counts)}  Max: {max(token_counts)}  Avg: {sum(token_counts) // len(token_counts)}")

    print("\n--- Embedding ---")
    try:
        from app.services.embedder import embed_chunks

        embeddings = embed_chunks(chunks)
        dims = [len(v) for v in embeddings]
        print(f"  Vectors: {len(embeddings)} x {dims[0]}d")
        if dims and dims[0] != 2048:
            print(f"  WARN: expected 2048-dim, got {dims[0]}")
    except Exception as exc:
        print(f"  SKIP: {exc}")

    print("\nDone.")


if __name__ == "__main__":
    main()
