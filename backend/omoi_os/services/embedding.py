"""Embedding service for generating text embeddings."""

from typing import List, Optional, TYPE_CHECKING
from enum import Enum
import logging
import threading

import numpy as np

from omoi_os.config import get_app_settings

if TYPE_CHECKING:
    from fastembed import TextEmbedding
    from openai import OpenAI

logger = logging.getLogger(__name__)


class EmbeddingProvider(str, Enum):
    """Embedding provider options."""

    OPENAI = "openai"
    LOCAL = "local"


# Singleton for local FastEmbed model to avoid re-downloading/loading
_local_model_instance: Optional["TextEmbedding"] = None
_local_model_lock = threading.Lock()
_local_model_loading = threading.Event()


def _get_local_model(
    model_name: str, cache_dir: Optional[str] = None
) -> "TextEmbedding":
    """
    Get or create a singleton FastEmbed model instance.

    This ensures the model is only loaded once and shared across all
    EmbeddingService instances.

    Args:
        model_name: Name of the FastEmbed model.
        cache_dir: Optional directory to cache downloaded models.

    Returns:
        The shared TextEmbedding instance.
    """
    global _local_model_instance

    if _local_model_instance is not None:
        return _local_model_instance

    with _local_model_lock:
        # Double-check after acquiring lock
        if _local_model_instance is not None:
            return _local_model_instance

        try:
            from fastembed import TextEmbedding
            import os

            # Expand ~ in cache_dir path
            resolved_cache_dir = None
            if cache_dir:
                resolved_cache_dir = os.path.expanduser(cache_dir)
                # Ensure cache directory exists
                os.makedirs(resolved_cache_dir, exist_ok=True)

            logger.info(
                f"Loading FastEmbed model: {model_name} (cache_dir={resolved_cache_dir})"
            )

            # Build kwargs for TextEmbedding
            kwargs = {"model_name": model_name}
            if resolved_cache_dir:
                kwargs["cache_dir"] = resolved_cache_dir

            _local_model_instance = TextEmbedding(**kwargs)
            _local_model_loading.set()  # Signal that loading is complete

            logger.info(f"FastEmbed model loaded successfully: {model_name}")
            return _local_model_instance

        except ImportError:
            raise ImportError("fastembed not installed. Run: uv add fastembed")


def preload_embedding_model() -> None:
    """
    Preload the local embedding model in a background thread.

    Call this at application startup if you want the model ready
    immediately without blocking the main thread.
    """
    embedding_settings = get_app_settings().embedding

    if embedding_settings.provider != "local":
        return

    if not embedding_settings.preload_in_background:
        return

    def _background_load():
        try:
            _get_local_model(
                model_name=embedding_settings.model_name,
                cache_dir=embedding_settings.cache_dir,
            )
        except Exception as e:
            logger.error(f"Background model preload failed: {e}")

    thread = threading.Thread(target=_background_load, daemon=True)
    thread.start()
    logger.info("Started background preload of embedding model")


def wait_for_model_ready(timeout: Optional[float] = None) -> bool:
    """
    Wait for the embedding model to finish loading.

    Useful for health checks or ensuring the model is ready before serving requests.

    Args:
        timeout: Maximum seconds to wait. None = wait indefinitely.

    Returns:
        True if model is ready, False if timeout occurred.
    """
    return _local_model_loading.wait(timeout=timeout)


def is_model_loaded() -> bool:
    """Check if the embedding model is already loaded."""
    return _local_model_instance is not None


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

    Performance optimizations:
    - Models are cached in a configurable directory (embedding.cache_dir)
    - Local models use a singleton pattern (loaded once, shared app-wide)
    - Lazy loading defers model initialization until first use
    - Optional background preloading (embedding.preload_in_background)
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
        self._cache_dir = embedding_settings.cache_dir
        self._lazy_load = embedding_settings.lazy_load

        # Lazy-loaded clients (initialized on first use)
        self._openai_client: Optional["OpenAI"] = None
        self._local_model: Optional["TextEmbedding"] = None

        # Set model names
        if self.provider == EmbeddingProvider.OPENAI:
            default_openai_model = (
                embedding_settings.model_name or "text-embedding-3-small"
            )
            self.model_name = model_name or default_openai_model
            self.dimensions = 1536
            if not self._lazy_load:
                self._init_openai()
        else:
            default_local_model = (
                embedding_settings.model_name or "intfloat/multilingual-e5-large"
            )
            self.model_name = model_name or default_local_model
            self.dimensions = 1536  # Padded to match OpenAI
            if not self._lazy_load:
                self._init_local()

    def _init_openai(self) -> None:
        """Initialize OpenAI client (lazy)."""
        if self._openai_client is not None:
            return

        if not self.openai_api_key:
            raise ValueError(
                "OpenAI API key required for OpenAI embeddings. "
                "Configure embedding.openai_api_key in YAML or EMBEDDING_OPENAI_API_KEY env var."
            )
        try:
            from openai import OpenAI

            self._openai_client = OpenAI(api_key=self.openai_api_key)
        except ImportError:
            raise ImportError("openai package not installed. Run: uv add openai")

    @property
    def openai_client(self) -> "OpenAI":
        """Get OpenAI client, initializing lazily if needed."""
        if self._openai_client is None:
            self._init_openai()
        return self._openai_client  # type: ignore

    def _init_local(self) -> None:
        """Initialize local FastEmbed model using singleton pattern."""
        if self._local_model is not None:
            return
        self._local_model = _get_local_model(self.model_name, self._cache_dir)

    @property
    def local_model(self) -> "TextEmbedding":
        """Get local model, initializing lazily if needed."""
        if self._local_model is None:
            self._init_local()
        return self._local_model  # type: ignore

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

    def _generate_local_embedding(
        self, text: str, is_query: bool = False
    ) -> List[float]:
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

    def batch_generate_embeddings(
        self, texts: List[str], is_query: bool = False
    ) -> List[List[float]]:
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

    def _batch_generate_local_embeddings(
        self, texts: List[str], is_query: bool = False
    ) -> List[List[float]]:
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
