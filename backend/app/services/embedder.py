import logging
import time

import httpx

from app.config import settings
from app.services.chunker import ChunkData

logger = logging.getLogger(__name__)

_BASE = settings.OPENROUTER_BASE_URL or "https://openrouter.ai/api/v1"
_EMBED_MODEL = "nvidia/nemotron-3-embed-1b:free"
EMBEDDING_DIM = 768
_BATCH_SIZE = 16
_MAX_RETRIES = 3


def _embed_batch(texts: list[str]) -> list[list[float]]:
    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")

    url = f"{_BASE}/embeddings"
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    input_data = texts[0] if len(texts) == 1 else texts
    payload = {"model": _EMBED_MODEL, "input": input_data}

    response = httpx.post(url, headers=headers, json=payload, timeout=60.0)
    response.raise_for_status()
    data = response.json()

    if "data" not in data or not isinstance(data["data"], list):
        raise RuntimeError(f"Unexpected embedding response from OpenRouter: {data}")

    return [item["embedding"][:EMBEDDING_DIM] for item in data["data"]]


def _embed_with_retry(texts: list[str]) -> list[list[float]]:
    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            return _embed_batch(texts)
        except Exception as exc:
            last_error = exc
            logger.warning(
                "OpenRouter embedding attempt %d/%d failed: %s",
                attempt + 1,
                _MAX_RETRIES,
                exc,
            )
        if attempt < _MAX_RETRIES - 1:
            time.sleep(2**attempt)

    raise RuntimeError(
        f"OpenRouter embedding failed after {_MAX_RETRIES} attempts: {last_error}"
    )


def embed_chunks(chunks: list[ChunkData]) -> list[list[float]]:
    texts = [c.content for c in chunks]
    if not texts:
        return []

    embeddings: list[list[float]] = []
    for i in range(0, len(texts), _BATCH_SIZE):
        embeddings.extend(_embed_with_retry(texts[i : i + _BATCH_SIZE]))
    return embeddings


def embed_query(query: str) -> list[float]:
    if not query:
        return []
    return _embed_with_retry([query])[0]
