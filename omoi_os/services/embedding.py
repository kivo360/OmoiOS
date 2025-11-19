"""Embedding service for generating text embeddings."""

from typing import List, Optional
from enum import Enum

import numpy as np

from omoi_os.config import get_app_settings


class EmbeddingProvider(str, Enum):
    """Embedding provider options."""

    OPENAI = "openai"
    LOCAL = "local"


class EmbeddingService:
    """
    Service for generating text embeddings using OpenAI or local models.

    Supports:
    - OpenAI text-embedding-3-small (1536 dimensions, production)
    - FastEmbed intfloat/multilingual-e5-large (1024 dimensions, development)

    The service automatically pads local embeddings to 1536 dimensions for
    consistency with OpenAI embeddings.
    
    Note: multilingual-e5-large requires prefixes for optimal performance:
    - Use "query: " prefix for queries
    - Use "passage: " prefix for passages/documents
    - For symmetric tasks, use "query: " prefix for all inputs
    """

    def __init__(
        self,
        provider: Optional[EmbeddingProvider] = None,
        openai_api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        """
        Initialize embedding service.

        Args:
            provider: Embedding provider (openai or local). Defaults to settings.embedding.provider.
            openai_api_key: OpenAI API key. Defaults to settings.embedding.openai_api_key.
            model_name: Model name override. Defaults based on provider.
        """
        embedding_settings = get_app_settings().embedding

        resolved_provider = (
            provider.value if isinstance(provider, EmbeddingProvider) else provider
        )
        provider_value = resolved_provider or embedding_settings.provider
        self.provider = (
            provider_value
            if isinstance(provider_value, EmbeddingProvider)
            else EmbeddingProvider(provider_value)
        )
        self.openai_api_key = openai_api_key or embedding_settings.openai_api_key

        # Set model names
        if self.provider == EmbeddingProvider.OPENAI:
            default_openai_model = embedding_settings.model_name or "text-embedding-3-small"
            self.model_name = model_name or default_openai_model
            self.dimensions = 1536
            self._init_openai()
        else:
            default_local_model = embedding_settings.model_name or "intfloat/multilingual-e5-large"
            self.model_name = model_name or default_local_model
            self.dimensions = 1536  # Padded to match OpenAI
            self._init_local()

    def _init_openai(self) -> None:
        """Initialize OpenAI client."""
        if not self.openai_api_key:
            raise ValueError(
                "OpenAI API key required for OpenAI embeddings. "
                "Configure embedding.openai_api_key in YAML or EMBEDDING_OPENAI_API_KEY env var."
            )
        try:
            from openai import OpenAI

            self.openai_client = OpenAI(api_key=self.openai_api_key)
        except ImportError:
            raise ImportError("openai package not installed. Run: uv add openai")

    def _init_local(self) -> None:
        """Initialize local FastEmbed model."""
        try:
            from fastembed import TextEmbedding

            # FastEmbed uses model names directly (no sentence-transformers/ prefix needed)
            self.local_model = TextEmbedding(model_name=self.model_name)
        except ImportError:
            raise ImportError("fastembed not installed. Run: uv add fastembed")

    def generate_embedding(self, text: str, is_query: bool = False) -> List[float]:
        """
        Generate embedding vector for text.

        Args:
            text: Input text to embed.
            is_query: If True, adds "query: " prefix for multilingual-e5-large.
                     If False, adds "passage: " prefix (default for documents).

        Returns:
            1536-dimensional embedding vector.
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        if self.provider == EmbeddingProvider.OPENAI:
            return self._generate_openai_embedding(text)
        else:
            return self._generate_local_embedding(text, is_query=is_query)

    def _generate_openai_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API."""
        response = self.openai_client.embeddings.create(
            model=self.model_name,
            input=text,
        )
        return response.data[0].embedding

    def _generate_local_embedding(self, text: str, is_query: bool = False) -> List[float]:
        """Generate embedding using local FastEmbed model."""
        # multilingual-e5-large requires prefixes for optimal performance
        if "multilingual-e5" in self.model_name:
            prefix = "query: " if is_query else "passage: "
            prefixed_text = f"{prefix}{text}"
        else:
            prefixed_text = text
        
        # FastEmbed returns an iterator, get first (and only) result
        embedding_iter = self.local_model.embed([prefixed_text])
        base_embedding = next(embedding_iter)

        # Pad to 1536 dimensions for consistency with OpenAI
        padded = np.zeros(1536, dtype=np.float32)
        padded[: len(base_embedding)] = base_embedding

        return padded.tolist()

    def batch_generate_embeddings(self, texts: List[str], is_query: bool = False) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of input texts.
            is_query: If True, adds "query: " prefix for multilingual-e5-large.
                     If False, adds "passage: " prefix (default for documents).

        Returns:
            List of 1536-dimensional embedding vectors.
        """
        if not texts:
            return []

        if self.provider == EmbeddingProvider.OPENAI:
            return self._batch_generate_openai_embeddings(texts)
        else:
            return self._batch_generate_local_embeddings(texts, is_query=is_query)

    def _batch_generate_openai_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Batch generate embeddings using OpenAI API."""
        response = self.openai_client.embeddings.create(
            model=self.model_name,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def _batch_generate_local_embeddings(self, texts: List[str], is_query: bool = False) -> List[List[float]]:
        """Batch generate embeddings using local FastEmbed model."""
        # multilingual-e5-large requires prefixes for optimal performance
        if "multilingual-e5" in self.model_name:
            prefix = "query: " if is_query else "passage: "
            prefixed_texts = [f"{prefix}{text}" for text in texts]
        else:
            prefixed_texts = texts
        
        # FastEmbed returns an iterator for batch embeddings
        embedding_iter = self.local_model.embed(prefixed_texts)
        base_embeddings = list(embedding_iter)

        # Pad all embeddings to 1536 dimensions
        padded_embeddings = []
        for emb in base_embeddings:
            padded = np.zeros(1536, dtype=np.float32)
            padded[: len(emb)] = emb
            padded_embeddings.append(padded.tolist())

        return padded_embeddings

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector.
            vec2: Second vector.

        Returns:
            Similarity score between -1 and 1 (1 = identical).
        """
        if not vec1 or not vec2:
            return 0.0

        v1 = np.array(vec1)
        v2 = np.array(vec2)

        # Handle zero vectors
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(v1, v2) / (norm1 * norm2))

    @staticmethod
    def euclidean_distance(vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate Euclidean distance between two vectors.

        Args:
            vec1: First vector.
            vec2: Second vector.

        Returns:
            Distance (0 = identical, larger = more different).
        """
        if not vec1 or not vec2:
            return float("inf")

        v1 = np.array(vec1)
        v2 = np.array(vec2)

        return float(np.linalg.norm(v1 - v2))
