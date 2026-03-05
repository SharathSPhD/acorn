"""Embedding service wrapping Ollama /api/embeddings endpoint."""
__pattern__ = "Strategy"

import logging
from typing import Any

import httpx

from api.config import AcornSettings

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "nomic-embed-text"
_DIMENSION = 768


class EmbeddingService:
    """Generate vector embeddings via Ollama's /api/embeddings endpoint."""

    def __init__(self, settings: AcornSettings | None = None) -> None:
        if settings is None:
            from api.dependencies import get_settings
            settings = get_settings()
        ollama_base = settings.ollama_base_url
        self._url = f"{ollama_base}/api/embeddings"
        self._model = _DEFAULT_MODEL
        self._dimension = _DIMENSION

    async def embed(self, text: str) -> list[float]:
        """Generate a single embedding vector for the given text."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                self._url,
                json={"model": self._model, "prompt": text},
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            embedding = data.get("embedding", [])
            if len(embedding) != self._dimension:
                logger.warning(
                    "Expected %d-dim embedding, got %d",
                    self._dimension,
                    len(embedding),
                )
            return embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts (sequential calls)."""
        return [await self.embed(t) for t in texts]

    @property
    def dimension(self) -> int:
        return self._dimension
