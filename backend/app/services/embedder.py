import logging
from typing import Any

import httpx

from app.config import settings
from app.services.chunker import ChunkData

logger = logging.getLogger(__name__)

_LOCAL_MODEL: Any = None
_BASE = settings.OPENROUTER_BASE_URL or "https://openrouter.ai/api/v1"
EMBEDDING_DIM = 768


def get_local_model() -> Any:
    global _LOCAL_MODEL
    if _LOCAL_MODEL is None:
        logger.info("Initializing local fallback embedding model: sentence-transformers/all-mpnet-base-v2...")
        from sentence_transformers import SentenceTransformer

        _LOCAL_MODEL = SentenceTransformer("all-mpnet-base-v2")
    return _LOCAL_MODEL


def warmup_embedder() -> None:
    """Pre-load local fallback model at application startup to eliminate 1st-request latency."""
    try:
        get_local_model()
        logger.info("Local HuggingFace embedding model pre-loaded successfully.")
    except Exception as exc:
        logger.warning("Failed to pre-load local embedding model at startup: %s", exc)


def _embed_via_openrouter(texts: list[str]) -> list[list[float]] | None:
    if not settings.OPENROUTER_API_KEY:
        return None

    url = f"{_BASE}/embeddings"
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    input_data = texts[0] if len(texts) == 1 else texts
    payload = {
        "model": "nvidia/nemotron-3-embed-1b:free",
        "input": input_data,
    }

    response = httpx.post(url, headers=headers, json=payload, timeout=10.0)
    response.raise_for_status()
    data = response.json()

    if "data" in data and isinstance(data["data"], list):
        # Truncate vectors to EMBEDDING_DIM (768) to strictly match PostgreSQL VECTOR(768) schema
        raw_embeddings = [item["embedding"] for item in data["data"]]
        sliced_embeddings = [vec[:EMBEDDING_DIM] for vec in raw_embeddings]
        return sliced_embeddings
    return None


def embed_chunks(chunks: list[ChunkData]) -> list[list[float]]:
    texts = [c.content for c in chunks]
    if not texts:
        return []

    try:
        result = _embed_via_openrouter(texts)
        if result:
            return result
    except Exception as exc:
        logger.warning("OpenRouter embedding API call failed (%s). Falling back to local model.", exc)

    return _local_embed(texts)


def embed_query(query: str) -> list[float]:
    if not query:
        return []

    try:
        result = _embed_via_openrouter([query])
        if result and len(result) > 0:
            return result[0]
    except Exception as exc:
        logger.warning("OpenRouter embedding API call failed (%s). Falling back to local model.", exc)

    return _local_embed([query])[0]


def _local_embed(texts: list[str]) -> list[list[float]]:
    model = get_local_model()
    embeddings = model.encode(texts, show_progress_bar=False).tolist()
    return [vec[:EMBEDDING_DIM] for vec in embeddings]
