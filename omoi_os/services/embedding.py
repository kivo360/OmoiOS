"""Embedding service for generating text embeddings."""

import os
from typing import List, Optional
from enum import Enum

import numpy as np


class EmbeddingProvider(str, Enum):
    """Embedding provider options."""

    OPENAI = "openai"
    LOCAL = "local"


class EmbeddingService:
    """
    Service for generating text embeddings using OpenAI or local models.
    
    Supports:
    - OpenAI text-embedding-3-small (1536 dimensions, production)
    - sentence-transformers/all-MiniLM-L6-v2 (384 dimensions, development)
    
    The service automatically pads local embeddings to 1536 dimensions for
    consistency with OpenAI embeddings.
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
            provider: Embedding provider (openai or local). Defaults to env var EMBEDDING_PROVIDER.
            openai_api_key: OpenAI API key. Defaults to env var OPENAI_API_KEY.
            model_name: Model name override. Defaults based on provider.
        """
        self.provider = provider or EmbeddingProvider(
            os.getenv("EMBEDDING_PROVIDER", "local")
        )
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        
        # Set model names
        if self.provider == EmbeddingProvider.OPENAI:
            self.model_name = model_name or "text-embedding-3-small"
            self.dimensions = 1536
            self._init_openai()
        else:
            self.model_name = model_name or "sentence-transformers/all-MiniLM-L6-v2"
            self.dimensions = 1536  # Padded to match OpenAI
            self._init_local()

    def _init_openai(self) -> None:
        """Initialize OpenAI client."""
        if not self.openai_api_key:
            raise ValueError(
                "OpenAI API key required for OpenAI embeddings. "
                "Set OPENAI_API_KEY environment variable."
            )
        try:
            from openai import OpenAI
            self.openai_client = OpenAI(api_key=self.openai_api_key)
        except ImportError:
            raise ImportError(
                "openai package not installed. Run: uv add openai"
            )

    def _init_local(self) -> None:
        """Initialize local sentence-transformers model."""
        try:
            from sentence_transformers import SentenceTransformer
            self.local_model = SentenceTransformer(self.model_name)
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. Run: uv add sentence-transformers"
            )

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text.
        
        Args:
            text: Input text to embed.
            
        Returns:
            1536-dimensional embedding vector.
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        if self.provider == EmbeddingProvider.OPENAI:
            return self._generate_openai_embedding(text)
        else:
            return self._generate_local_embedding(text)

    def _generate_openai_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API."""
        response = self.openai_client.embeddings.create(
            model=self.model_name,
            input=text,
        )
        return response.data[0].embedding

    def _generate_local_embedding(self, text: str) -> List[float]:
        """Generate embedding using local sentence-transformers model."""
        # Generate base embedding (384 dimensions for MiniLM)
        base_embedding = self.local_model.encode(text, convert_to_numpy=True)
        
        # Pad to 1536 dimensions for consistency with OpenAI
        padded = np.zeros(1536, dtype=np.float32)
        padded[: len(base_embedding)] = base_embedding
        
        return padded.tolist()

    def batch_generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.
        
        Args:
            texts: List of input texts.
            
        Returns:
            List of 1536-dimensional embedding vectors.
        """
        if not texts:
            return []

        if self.provider == EmbeddingProvider.OPENAI:
            return self._batch_generate_openai_embeddings(texts)
        else:
            return self._batch_generate_local_embeddings(texts)

    def _batch_generate_openai_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Batch generate embeddings using OpenAI API."""
        response = self.openai_client.embeddings.create(
            model=self.model_name,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def _batch_generate_local_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Batch generate embeddings using local model."""
        base_embeddings = self.local_model.encode(texts, convert_to_numpy=True)
        
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

