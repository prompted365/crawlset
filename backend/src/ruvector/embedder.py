"""
RuVector Embedding Generator with caching.

Provides text embedding generation using sentence-transformers with
Redis caching for performance optimization.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

import numpy as np
from redis.asyncio import Redis
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Generate embeddings for text using sentence-transformers.

    Features:
    - Multiple model support with configurable dimensions
    - Batch processing for efficiency
    - Redis caching layer to avoid recomputing embeddings
    - Token counting and automatic chunking
    """

    # Model configurations
    MODELS = {
        "all-MiniLM-L6-v2": {"dims": 384, "max_seq_length": 256},
        "all-mpnet-base-v2": {"dims": 768, "max_seq_length": 384},
        "all-MiniLM-L12-v2": {"dims": 384, "max_seq_length": 256},
    }

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        redis_url: Optional[str] = None,
        cache_ttl: int = 86400 * 7,  # 7 days
        device: Optional[str] = None,
    ):
        """
        Initialize the embedding generator.

        Args:
            model_name: Name of the sentence-transformers model
            redis_url: Redis connection URL for caching (optional)
            cache_ttl: Cache TTL in seconds (default 7 days)
            device: Device to use ('cpu', 'cuda', or None for auto)
        """
        if model_name not in self.MODELS:
            raise ValueError(
                f"Unsupported model: {model_name}. "
                f"Supported models: {list(self.MODELS.keys())}"
            )

        self.model_name = model_name
        self.model_config = self.MODELS[model_name]
        self.cache_ttl = cache_ttl
        self.redis_url = redis_url
        self._redis: Optional[Redis] = None
        self._model: Optional[SentenceTransformer] = None
        self._device = device

        logger.info(
            f"Initialized EmbeddingGenerator with model={model_name}, "
            f"dims={self.model_config['dims']}"
        )

    async def initialize(self) -> None:
        """Initialize model and Redis connection."""
        # Load model in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        self._model = await loop.run_in_executor(
            None,
            lambda: SentenceTransformer(self.model_name, device=self._device)
        )
        logger.info(f"Loaded model {self.model_name}")

        # Initialize Redis if URL provided
        if self.redis_url:
            try:
                self._redis = Redis.from_url(
                    self.redis_url,
                    decode_responses=False,  # We'll handle binary data
                    socket_timeout=5,
                    socket_connect_timeout=5,
                )
                # Test connection
                await self._redis.ping()
                logger.info("Connected to Redis for embedding cache")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Caching disabled.")
                self._redis = None

    async def close(self) -> None:
        """Close connections and cleanup resources."""
        if self._redis:
            await self._redis.close()
            self._redis = None

    def _compute_cache_key(self, text: str) -> str:
        """Compute cache key for text."""
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        return f"embedding:{self.model_name}:{text_hash}"

    async def _get_cached_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get cached embedding from Redis."""
        if not self._redis:
            return None

        try:
            cache_key = self._compute_cache_key(text)
            cached = await self._redis.get(cache_key)
            if cached:
                # Deserialize numpy array
                embedding = np.frombuffer(cached, dtype=np.float32)
                logger.debug(f"Cache hit for text (len={len(text)})")
                return embedding
        except Exception as e:
            logger.warning(f"Cache read error: {e}")

        return None

    async def _cache_embedding(self, text: str, embedding: np.ndarray) -> None:
        """Cache embedding in Redis."""
        if not self._redis:
            return

        try:
            cache_key = self._compute_cache_key(text)
            # Serialize numpy array to bytes
            embedding_bytes = embedding.astype(np.float32).tobytes()
            await self._redis.setex(cache_key, self.cache_ttl, embedding_bytes)
            logger.debug(f"Cached embedding for text (len={len(text)})")
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    async def embed(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            Numpy array of shape (dims,)
        """
        if not self._model:
            await self.initialize()

        # Check cache first
        cached = await self._get_cached_embedding(text)
        if cached is not None:
            return cached

        # Generate embedding
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            lambda: self._model.encode(text, convert_to_numpy=True)
        )

        # Cache result
        await self._cache_embedding(text, embedding)

        return embedding

    async def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = False,
    ) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts in batches.

        Args:
            texts: List of input texts
            batch_size: Number of texts to process per batch
            show_progress: Show progress bar (requires tqdm)

        Returns:
            List of numpy arrays, each of shape (dims,)
        """
        if not self._model:
            await self.initialize()

        if not texts:
            return []

        # Check cache for all texts
        embeddings: List[Optional[np.ndarray]] = []
        texts_to_embed: List[tuple[int, str]] = []

        for idx, text in enumerate(texts):
            cached = await self._get_cached_embedding(text)
            if cached is not None:
                embeddings.append(cached)
            else:
                embeddings.append(None)
                texts_to_embed.append((idx, text))

        if not texts_to_embed:
            return embeddings  # All cached

        logger.info(
            f"Computing embeddings for {len(texts_to_embed)}/{len(texts)} texts "
            f"(batch_size={batch_size})"
        )

        # Generate embeddings for uncached texts
        loop = asyncio.get_event_loop()
        texts_only = [text for _, text in texts_to_embed]

        new_embeddings = await loop.run_in_executor(
            None,
            lambda: self._model.encode(
                texts_only,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True,
            )
        )

        # Cache new embeddings and fill results
        for (idx, text), embedding in zip(texts_to_embed, new_embeddings):
            embeddings[idx] = embedding
            await self._cache_embedding(text, embedding)

        return embeddings

    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        This is a rough approximation based on whitespace splitting.
        For more accurate counts, use a tokenizer.

        Args:
            text: Input text

        Returns:
            Approximate token count
        """
        # Simple approximation: split on whitespace
        return len(text.split())

    def chunk_text(
        self,
        text: str,
        max_tokens: Optional[int] = None,
        overlap: int = 50,
    ) -> List[str]:
        """
        Split text into chunks suitable for embedding.

        Args:
            text: Input text to chunk
            max_tokens: Maximum tokens per chunk (defaults to model's max_seq_length)
            overlap: Number of overlapping tokens between chunks

        Returns:
            List of text chunks
        """
        if max_tokens is None:
            max_tokens = self.model_config["max_seq_length"]

        words = text.split()
        chunks = []

        if len(words) <= max_tokens:
            return [text]

        start = 0
        while start < len(words):
            end = min(start + max_tokens, len(words))
            chunk = " ".join(words[start:end])
            chunks.append(chunk)

            # Move to next chunk with overlap
            start = end - overlap
            if start >= len(words):
                break

        logger.debug(f"Split text into {len(chunks)} chunks (max_tokens={max_tokens})")
        return chunks

    async def embed_documents(
        self,
        documents: List[Dict[str, Any]],
        text_field: str = "text",
        batch_size: int = 32,
    ) -> List[Dict[str, Any]]:
        """
        Embed multiple documents with metadata preservation.

        Args:
            documents: List of document dicts
            text_field: Field name containing text to embed
            batch_size: Batch size for embedding

        Returns:
            List of documents with 'embedding' field added
        """
        texts = [doc[text_field] for doc in documents]
        embeddings = await self.embed_batch(texts, batch_size=batch_size)

        # Add embeddings to documents
        result = []
        for doc, embedding in zip(documents, embeddings):
            doc_copy = doc.copy()
            doc_copy["embedding"] = embedding
            result.append(doc_copy)

        return result

    @property
    def embedding_dimension(self) -> int:
        """Get the embedding dimension for the current model."""
        return self.model_config["dims"]

    @property
    def max_sequence_length(self) -> int:
        """Get the maximum sequence length for the current model."""
        return self.model_config["max_seq_length"]

    def __repr__(self) -> str:
        return (
            f"EmbeddingGenerator(model={self.model_name}, "
            f"dims={self.embedding_dimension}, "
            f"cache_enabled={self._redis is not None})"
        )


async def create_embedder(
    model_name: str = "all-MiniLM-L6-v2",
    redis_url: Optional[str] = None,
) -> EmbeddingGenerator:
    """
    Factory function to create and initialize an EmbeddingGenerator.

    Args:
        model_name: Sentence-transformers model name
        redis_url: Redis URL for caching (optional)

    Returns:
        Initialized EmbeddingGenerator
    """
    embedder = EmbeddingGenerator(model_name=model_name, redis_url=redis_url)
    await embedder.initialize()
    return embedder
