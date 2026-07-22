from langchain_openai import OpenAIEmbeddings

from app.config import settings
from app.services.chunker import ChunkData


def embed_chunks(chunks: list[ChunkData]) -> list[list[float]]:
    texts = [c.content for c in chunks]
    if not texts:
        return []

    try:
        emb = OpenAIEmbeddings(
            model="nvidia/nemotron-3-embed-1b:free",
            openai_api_key=settings.OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
        )
        return emb.embed_documents(texts)
    except Exception:
        return _local_embed(texts)


def embed_query(query: str) -> list[float]:
    if not query:
        return []

    try:
        emb = OpenAIEmbeddings(
            model="nvidia/nemotron-3-embed-1b:free",
            openai_api_key=settings.OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
        )
        return emb.embed_query(query)
    except Exception:
        return _local_embed([query])[0]


def _local_embed(texts: list[str]) -> list[list[float]]:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-mpnet-base-v2")
    return model.encode(texts, show_progress_bar=False).tolist()
