"""Embedding service for generating text embeddings."""

import threading
import time
from enum import Enum
from typing import List, Optional, TYPE_CHECKING

import numpy as np

from omoi_os.config import get_app_settings
from omoi_os.logging import get_logger

if TYPE_CHECKING:
    from fastembed import TextEmbedding
    from openai import OpenAI

logger = get_logger(__name__)

# Default embedding dimensions - must match pgvector column definitions
# pgvector supports up to 16,000 dimensions for storage, but standard indexing
# (HNSW/IVFFlat) is limited to 2,000 dimensions. Using 1536 for compatibility.
DEFAULT_EMBEDDING_DIMENSIONS = 1536

# Retry configuration for API calls
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds
RETRY_MAX_DELAY = 10.0  # seconds


class EmbeddingProvider(str, Enum):
    """Embedding provider options."""

    FIREWORKS = "fireworks"  # Fireworks AI - fast, affordable, OpenAI-compatible
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
    # If model is already loaded, return immediately
    if _local_model_instance is not None:
        return True
    # Otherwise wait for the loading event
    return _local_model_loading.wait(timeout=timeout)


def is_model_loaded() -> bool:
    """Check if the embedding model is already loaded."""
    return _local_model_instance is not None


def get_local_model_instance() -> Optional["TextEmbedding"]:
    """
    Get the current local model instance if it's loaded.

    Returns:
        The TextEmbedding instance if loaded, None otherwise.
    """
    return _local_model_instance


class EmbeddingService:
    """
    Service for generating text embeddings using Fireworks AI, OpenAI, or local models.

    Supports:
    - Fireworks AI qwen3-embedding-8b (1536 dimensions default, fast & affordable) [DEFAULT]
    - OpenAI text-embedding-3-small (1536 dimensions, production)
    - FastEmbed intfloat/multilingual-e5-large (1024 dimensions, local/no API)

    Note: Dimensions are set to 1536 by default for pgvector compatibility.
    pgvector supports up to 16,000 dimensions for storage, but standard indexing
    (HNSW/IVFFlat) is limited to 2,000 dimensions.

    The service automatically pads local embeddings to 1536 dimensions for
    consistency with OpenAI embeddings.

    Configuration (via env vars or YAML):
        EMBEDDING_PROVIDER: "fireworks" | "openai" | "local"
        EMBEDDING_FIREWORKS_API_KEY: Your Fireworks AI API key
        EMBEDDING_OPENAI_API_KEY: Your OpenAI API key
        EMBEDDING_MODEL_NAME: Override model name
        EMBEDDING_DIMENSIONS: Override output dimensions

    Note: multilingual-e5-large (local) requires prefixes for optimal performance:
    - Use "query: " prefix for queries
    - Use "passage: " prefix for passages/documents

    Performance optimizations:
    - Fireworks/OpenAI: Lazy client initialization, no model loading
    - Local: Models cached in embedding.cache_dir, singleton pattern
    - All: Lazy loading defers initialization until first use
    """

    # Fireworks AI API base URL (OpenAI-compatible)
    FIREWORKS_BASE_URL = "https://api.fireworks.ai/inference/v1"

    def __init__(
        self,
        provider: Optional[EmbeddingProvider] = None,
        fireworks_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        """
        Initialize embedding service.

        Args:
            provider: Embedding provider (fireworks, openai, or local).
                      Defaults to settings.embedding.provider.
            fireworks_api_key: Fireworks AI API key. Defaults to settings.embedding.fireworks_api_key.
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

        # Store API keys
        self.fireworks_api_key = (
            fireworks_api_key or embedding_settings.fireworks_api_key
        )
        self.openai_api_key = openai_api_key or embedding_settings.openai_api_key
        self._cache_dir = embedding_settings.cache_dir
        self._lazy_load = embedding_settings.lazy_load
        self._configured_dimensions = embedding_settings.dimensions

        # Lazy-loaded clients (initialized on first use)
        self._fireworks_client: Optional["OpenAI"] = None
        self._openai_client: Optional["OpenAI"] = None
        self._local_model: Optional["TextEmbedding"] = None

        # Set model names and dimensions based on provider
        # Note: Only use config model_name if it matches the provider type,
        # otherwise use provider-specific defaults
        config_model = embedding_settings.model_name
        config_provider = embedding_settings.provider

        if self.provider == EmbeddingProvider.FIREWORKS:
            # Use config model only if config is also set to fireworks
            if config_provider == "fireworks" and config_model:
                default_model = config_model
            else:
                default_model = "fireworks/qwen3-embedding-8b"
            self.model_name = model_name or default_model
            # Use DEFAULT_EMBEDDING_DIMENSIONS for pgvector compatibility (max 2000 for standard indexing)
            # Qwen3 supports variable dimensions via API parameter
            self.dimensions = (
                self._configured_dimensions or DEFAULT_EMBEDDING_DIMENSIONS
            )
            if not self._lazy_load:
                self._init_fireworks()
        elif self.provider == EmbeddingProvider.OPENAI:
            # Use config model only if config is also set to openai
            if config_provider == "openai" and config_model:
                default_model = config_model
            else:
                default_model = "text-embedding-3-small"
            self.model_name = model_name or default_model
            self.dimensions = (
                self._configured_dimensions or DEFAULT_EMBEDDING_DIMENSIONS
            )
            if not self._lazy_load:
                self._init_openai()
        else:  # LOCAL
            # Use config model only if config is also set to local
            if config_provider == "local" and config_model:
                default_model = config_model
            else:
                default_model = "intfloat/multilingual-e5-large"
            self.model_name = model_name or default_model
            self.dimensions = (
                DEFAULT_EMBEDDING_DIMENSIONS  # Padded to match API providers
            )
            if not self._lazy_load:
                self._init_local()

    def _init_fireworks(self) -> None:
        """Initialize Fireworks AI client (lazy, OpenAI-compatible)."""
        if self._fireworks_client is not None:
            return

        if not self.fireworks_api_key:
            raise ValueError(
                "Fireworks API key required for Fireworks embeddings. "
                "Configure embedding.fireworks_api_key in YAML or EMBEDDING_FIREWORKS_API_KEY env var."
            )
        try:
            from openai import OpenAI

            self._fireworks_client = OpenAI(
                api_key=self.fireworks_api_key,
                base_url=self.FIREWORKS_BASE_URL,
            )
            logger.info(
                f"Initialized Fireworks AI client with model: {self.model_name}"
            )
        except ImportError:
            raise ImportError("openai package not installed. Run: uv add openai")

    @property
    def fireworks_client(self) -> "OpenAI":
        """Get Fireworks client, initializing lazily if needed."""
        if self._fireworks_client is None:
            self._init_fireworks()
        return self._fireworks_client  # type: ignore

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
            Embedding vector (dimensions depend on provider/model).
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        if self.provider == EmbeddingProvider.FIREWORKS:
            return self._generate_fireworks_embedding(text)
        elif self.provider == EmbeddingProvider.OPENAI:
            return self._generate_openai_embedding(text)
        else:
            return self._generate_local_embedding(text, is_query=is_query)

    def _generate_fireworks_embedding(self, text: str) -> List[float]:
        """Generate embedding using Fireworks AI API (OpenAI-compatible) with retry."""
        kwargs = {
            "model": self.model_name,
            "input": text,
        }
        # Add dimensions if configured (for variable-length embeddings)
        if self._configured_dimensions:
            kwargs["dimensions"] = self._configured_dimensions

        embedding = self._call_with_retry(
            lambda: self.fireworks_client.embeddings.create(**kwargs).data[0].embedding,
            "Fireworks embedding",
        )
        return self._validate_embedding(embedding)

    def _generate_openai_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API with retry."""
        embedding = self._call_with_retry(
            lambda: self.openai_client.embeddings.create(
                model=self.model_name,
                input=text,
            )
            .data[0]
            .embedding,
            "OpenAI embedding",
        )
        return self._validate_embedding(embedding)

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

        # Pad to DEFAULT_EMBEDDING_DIMENSIONS for consistency with API providers
        padded = np.zeros(DEFAULT_EMBEDDING_DIMENSIONS, dtype=np.float32)
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
            List of embedding vectors (dimensions depend on provider/model).
        """
        if not texts:
            return []

        if self.provider == EmbeddingProvider.FIREWORKS:
            return self._batch_generate_fireworks_embeddings(texts)
        elif self.provider == EmbeddingProvider.OPENAI:
            return self._batch_generate_openai_embeddings(texts)
        else:
            return self._batch_generate_local_embeddings(texts, is_query=is_query)

    def _batch_generate_fireworks_embeddings(
        self, texts: List[str]
    ) -> List[List[float]]:
        """Batch generate embeddings using Fireworks AI API (OpenAI-compatible) with retry."""
        kwargs = {
            "model": self.model_name,
            "input": texts,
        }
        # Add dimensions if configured (for variable-length embeddings)
        if self._configured_dimensions:
            kwargs["dimensions"] = self._configured_dimensions

        embeddings = self._call_with_retry(
            lambda: [
                item.embedding
                for item in self.fireworks_client.embeddings.create(**kwargs).data
            ],
            "Fireworks batch embedding",
        )
        return [self._validate_embedding(emb) for emb in embeddings]

    def _batch_generate_openai_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Batch generate embeddings using OpenAI API with retry."""
        embeddings = self._call_with_retry(
            lambda: [
                item.embedding
                for item in self.openai_client.embeddings.create(
                    model=self.model_name,
                    input=texts,
                ).data
            ],
            "OpenAI batch embedding",
        )
        return [self._validate_embedding(emb) for emb in embeddings]

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

        # Pad all embeddings to DEFAULT_EMBEDDING_DIMENSIONS
        padded_embeddings = []
        for emb in base_embeddings:
            padded = np.zeros(DEFAULT_EMBEDDING_DIMENSIONS, dtype=np.float32)
            padded[: len(emb)] = emb
            padded_embeddings.append(padded.tolist())

        return padded_embeddings

    def _call_with_retry(self, func, operation_name: str):
        """
        Call a function with exponential backoff retry on transient failures.

        Args:
            func: Callable to execute
            operation_name: Name for logging purposes

        Returns:
            Result of the function call

        Raises:
            Exception: After all retries exhausted
        """
        last_exception = None

        for attempt in range(MAX_RETRIES):
            try:
                return func()
            except Exception as e:
                last_exception = e
                error_type = type(e).__name__

                # Check if error is retryable (rate limits, timeouts, server errors)
                retryable = any(
                    indicator in str(e).lower()
                    for indicator in [
                        "rate limit",
                        "timeout",
                        "503",
                        "502",
                        "429",
                        "connection",
                        "temporarily",
                    ]
                )

                if not retryable or attempt == MAX_RETRIES - 1:
                    logger.error(
                        f"{operation_name} failed after {attempt + 1} attempts: {error_type}: {e}"
                    )
                    raise

                # Exponential backoff with jitter
                delay = min(
                    RETRY_BASE_DELAY * (2**attempt) + np.random.uniform(0, 1),
                    RETRY_MAX_DELAY,
                )
                logger.warning(
                    f"{operation_name} failed ({error_type}), retrying in {delay:.1f}s "
                    f"(attempt {attempt + 1}/{MAX_RETRIES})"
                )
                time.sleep(delay)

        # Should not reach here, but just in case
        raise last_exception  # type: ignore

    def _validate_embedding(self, embedding: List[float]) -> List[float]:
        """
        Validate embedding dimensions match expected configuration.

        Args:
            embedding: The embedding vector to validate

        Returns:
            The validated embedding

        Raises:
            ValueError: If embedding dimensions don't match expected
        """
        expected_dims = self.dimensions
        actual_dims = len(embedding)

        if actual_dims != expected_dims:
            logger.warning(
                f"Embedding dimension mismatch: got {actual_dims}, expected {expected_dims}. "
                f"This may cause pgvector indexing issues."
            )
            # Truncate or pad to match expected dimensions
            if actual_dims > expected_dims:
                logger.info(
                    f"Truncating embedding from {actual_dims} to {expected_dims}"
                )
                return embedding[:expected_dims]
            else:
                logger.info(f"Padding embedding from {actual_dims} to {expected_dims}")
                padded = list(embedding) + [0.0] * (expected_dims - actual_dims)
                return padded

        return embedding

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
