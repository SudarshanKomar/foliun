import logging
from functools import lru_cache
from typing import Protocol

from foliun.config import Settings, get_settings

logger = logging.getLogger(__name__)


class Embedder(Protocol):
    """Protocol for text embedding services."""

    def embed_texts(self, texts: list[str], is_query: bool = False) -> list[list[float]]:
        """Embed a list of texts."""


class LocalBgeEmbedder:
    """Local BGE embedding model wrapper."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Load the local embedding model."""

        from sentence_transformers import SentenceTransformer

        self.settings = settings or get_settings()
        self.model = SentenceTransformer(self.settings.embedding_model_name)
        test_vector = self.embed_texts(["dimension validation"])[0]
        if len(test_vector) != self.settings.embedding_dimensions:
            logger.critical(
                "Embedding dimension validation failed",
                extra={
                    "model": self.settings.embedding_model_name,
                    "expected_dimensions": self.settings.embedding_dimensions,
                    "actual_dimensions": len(test_vector),
                },
            )
            raise RuntimeError("Embedding model produced incompatible dimensions")

    def embed_texts(self, texts: list[str], is_query: bool = False) -> list[list[float]]:
        """Embed a list of texts using BAAI/bge-base-en-v1.5."""

        inputs = texts
        if is_query:
            inputs = [f"Represent this sentence for searching relevant passages: {text}" for text in texts]
        vectors = self.model.encode(
            inputs,
            batch_size=self.settings.embedding_batch_size,
            normalize_embeddings=True,
        )
        return [vector.tolist() for vector in vectors]


class DeterministicFakeEmbedder:
    """Deterministic embedder for tests and lightweight local runs."""

    def __init__(self, dimensions: int = 768) -> None:
        """Initialize fake embedder."""

        self.dimensions = dimensions

    def embed_texts(self, texts: list[str], is_query: bool = False) -> list[list[float]]:
        """Return deterministic pseudo-embeddings."""

        embeddings: list[list[float]] = []
        for text in texts:
            seed = sum(ord(char) for char in text) or 1
            embeddings.append([((seed + index) % 997) / 997 for index in range(self.dimensions)])
        return embeddings


@lru_cache
def get_embedder() -> LocalBgeEmbedder:
    """Return the process-wide local embedding model."""

    return LocalBgeEmbedder()
