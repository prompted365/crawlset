"""
RuVector Client for vector database operations.

Provides async interface to RuVector for document storage, retrieval,
and hybrid search with graph capabilities.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import hnswlib
import numpy as np

from .embedder import EmbeddingGenerator

logger = logging.getLogger(__name__)


class RuVectorClient:
    """
    Async client for RuVector operations.

    Features:
    - Document insertion with auto-embedding
    - Bulk insert operations
    - Hybrid search (semantic + lexical)
    - Graph query support
    - HNSW index for fast vector search
    - File-based persistence
    """

    def __init__(
        self,
        data_dir: Union[str, Path],
        embedding_model: str = "all-MiniLM-L6-v2",
        redis_url: Optional[str] = None,
        index_params: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize RuVector client.

        Args:
            data_dir: Directory for storing vector data and indices
            embedding_model: Sentence-transformers model name
            redis_url: Redis URL for embedding cache
            index_params: HNSW index parameters (ef_construction, M)
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.embedding_model = embedding_model
        self.redis_url = redis_url

        # HNSW index parameters
        self.index_params = index_params or {
            "ef_construction": 200,  # Higher = better quality, slower build
            "M": 16,  # Number of connections per element
            "ef": 50,  # Higher = better search quality, slower
        }

        # State
        self._embedder: Optional[EmbeddingGenerator] = None
        self._index: Optional[hnswlib.Index] = None
        self._documents: Dict[str, Dict[str, Any]] = {}
        self._id_to_label: Dict[str, int] = {}
        self._label_to_id: Dict[int, str] = {}
        self._next_label = 0
        self._initialized = False

        logger.info(f"RuVectorClient initialized at {self.data_dir}")

    async def initialize(self) -> None:
        """Initialize embedder and load existing index if present."""
        if self._initialized:
            return

        # Initialize embedder
        from .embedder import create_embedder
        self._embedder = await create_embedder(
            model_name=self.embedding_model,
            redis_url=self.redis_url,
        )

        # Load existing index and documents
        await self._load_index()
        await self._load_documents()

        self._initialized = True
        logger.info(
            f"RuVectorClient initialized with {len(self._documents)} documents"
        )

    async def _load_index(self) -> None:
        """Load HNSW index from disk if it exists."""
        index_path = self.data_dir / "index.bin"
        metadata_path = self.data_dir / "index_metadata.json"

        if index_path.exists() and metadata_path.exists():
            try:
                # Load metadata
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)

                # Create index with saved parameters
                dim = metadata["dimension"]
                self._index = hnswlib.Index(space="cosine", dim=dim)

                # Load index
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self._index.load_index(
                        str(index_path),
                        max_elements=metadata.get("max_elements", 10000),
                    )
                )

                # Restore mappings
                self._id_to_label = {
                    doc_id: int(label)
                    for doc_id, label in metadata.get("id_to_label", {}).items()
                }
                self._label_to_id = {
                    int(label): doc_id
                    for doc_id, label in metadata.get("id_to_label", {}).items()
                }
                self._next_label = metadata.get("next_label", 0)

                logger.info(f"Loaded index with {len(self._id_to_label)} vectors")

            except Exception as e:
                logger.error(f"Failed to load index: {e}")
                self._index = None
        else:
            logger.info("No existing index found, will create new one")

    async def _save_index(self) -> None:
        """Save HNSW index to disk."""
        if not self._index:
            return

        try:
            index_path = self.data_dir / "index.bin"
            metadata_path = self.data_dir / "index_metadata.json"

            # Save index
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._index.save_index(str(index_path))
            )

            # Save metadata
            metadata = {
                "dimension": self._embedder.embedding_dimension,
                "max_elements": self._index.get_max_elements(),
                "id_to_label": {doc_id: str(label) for doc_id, label in self._id_to_label.items()},
                "next_label": self._next_label,
                "index_params": self.index_params,
            }

            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            logger.debug(f"Saved index with {len(self._id_to_label)} vectors")

        except Exception as e:
            logger.error(f"Failed to save index: {e}")

    async def _load_documents(self) -> None:
        """Load document metadata from disk."""
        docs_path = self.data_dir / "documents.json"

        if docs_path.exists():
            try:
                with open(docs_path, "r") as f:
                    self._documents = json.load(f)
                logger.info(f"Loaded {len(self._documents)} documents")
            except Exception as e:
                logger.error(f"Failed to load documents: {e}")
                self._documents = {}
        else:
            logger.info("No existing documents found")

    async def _save_documents(self) -> None:
        """Save document metadata to disk."""
        docs_path = self.data_dir / "documents.json"

        try:
            with open(docs_path, "w") as f:
                json.dump(self._documents, f, indent=2)
            logger.debug(f"Saved {len(self._documents)} documents")
        except Exception as e:
            logger.error(f"Failed to save documents: {e}")

    def _ensure_index(self, dimension: int) -> None:
        """Ensure HNSW index exists with proper dimension."""
        if self._index is None:
            self._index = hnswlib.Index(space="cosine", dim=dimension)
            self._index.init_index(
                max_elements=10000,
                ef_construction=self.index_params["ef_construction"],
                M=self.index_params["M"],
            )
            self._index.set_ef(self.index_params["ef"])
            logger.info(f"Created new HNSW index (dim={dimension})")

    async def insert_document(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[np.ndarray] = None,
    ) -> str:
        """
        Insert a single document into RuVector.

        Args:
            doc_id: Unique document identifier
            text: Document text content
            metadata: Additional metadata to store
            embedding: Pre-computed embedding (optional, will generate if not provided)

        Returns:
            Document ID
        """
        if not self._initialized:
            await self.initialize()

        # Generate embedding if not provided
        if embedding is None:
            embedding = await self._embedder.embed(text)

        # Ensure index exists
        self._ensure_index(len(embedding))

        # Get or create label for this document
        if doc_id in self._id_to_label:
            # Update existing document
            label = self._id_to_label[doc_id]
            logger.debug(f"Updating document {doc_id}")
        else:
            # New document
            label = self._next_label
            self._id_to_label[doc_id] = label
            self._label_to_id[label] = doc_id
            self._next_label += 1
            logger.debug(f"Inserting new document {doc_id}")

        # Add to index
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._index.add_items([embedding], [label])
        )

        # Store document metadata
        self._documents[doc_id] = {
            "id": doc_id,
            "text": text,
            "metadata": metadata or {},
            "label": label,
        }

        # Persist changes
        await self._save_index()
        await self._save_documents()

        return doc_id

    async def bulk_insert(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 32,
    ) -> List[str]:
        """
        Bulk insert multiple documents.

        Args:
            documents: List of dicts with 'id', 'text', and optional 'metadata'
            batch_size: Batch size for embedding generation

        Returns:
            List of inserted document IDs
        """
        if not self._initialized:
            await self.initialize()

        if not documents:
            return []

        logger.info(f"Bulk inserting {len(documents)} documents")

        # Generate embeddings for all documents
        texts = [doc["text"] for doc in documents]
        embeddings = await self._embedder.embed_batch(texts, batch_size=batch_size)

        # Ensure index exists
        self._ensure_index(len(embeddings[0]))

        # Prepare labels and data
        labels = []
        doc_ids = []

        for doc, embedding in zip(documents, embeddings):
            doc_id = doc["id"]
            doc_ids.append(doc_id)

            # Get or create label
            if doc_id in self._id_to_label:
                label = self._id_to_label[doc_id]
            else:
                label = self._next_label
                self._id_to_label[doc_id] = label
                self._label_to_id[label] = doc_id
                self._next_label += 1

            labels.append(label)

            # Store document metadata
            self._documents[doc_id] = {
                "id": doc_id,
                "text": doc["text"],
                "metadata": doc.get("metadata", {}),
                "label": label,
            }

        # Add all to index
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._index.add_items(embeddings, labels)
        )

        # Persist changes
        await self._save_index()
        await self._save_documents()

        logger.info(f"Bulk inserted {len(doc_ids)} documents")
        return doc_ids

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search (semantic only for now, will integrate with search.py).

        Args:
            query: Search query text
            top_k: Number of results to return
            filter_metadata: Metadata filters to apply

        Returns:
            List of search results with scores
        """
        if not self._initialized:
            await self.initialize()

        if not self._index or len(self._documents) == 0:
            return []

        # Generate query embedding
        query_embedding = await self._embedder.embed(query)

        # Search index
        loop = asyncio.get_event_loop()
        labels, distances = await loop.run_in_executor(
            None,
            lambda: self._index.knn_query([query_embedding], k=top_k)
        )

        # Convert results
        results = []
        for label, distance in zip(labels[0], distances[0]):
            doc_id = self._label_to_id.get(label)
            if doc_id and doc_id in self._documents:
                doc = self._documents[doc_id]

                # Apply metadata filtering
                if filter_metadata:
                    doc_meta = doc.get("metadata", {})
                    if not all(
                        doc_meta.get(k) == v for k, v in filter_metadata.items()
                    ):
                        continue

                # Convert distance to similarity score (1 - cosine distance)
                similarity = 1.0 - distance

                results.append({
                    "id": doc_id,
                    "text": doc["text"],
                    "metadata": doc.get("metadata", {}),
                    "score": float(similarity),
                })

        return results

    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by ID.

        Args:
            doc_id: Document identifier

        Returns:
            Document dict or None if not found
        """
        if not self._initialized:
            await self.initialize()

        return self._documents.get(doc_id)

    async def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document from RuVector.

        Args:
            doc_id: Document identifier

        Returns:
            True if deleted, False if not found
        """
        if not self._initialized:
            await self.initialize()

        if doc_id not in self._documents:
            return False

        # Note: HNSW doesn't support deletion, so we just mark as deleted
        # A full rebuild would be needed to reclaim space
        label = self._id_to_label.get(doc_id)
        if label is not None:
            del self._id_to_label[doc_id]
            del self._label_to_id[label]

        del self._documents[doc_id]

        await self._save_documents()
        logger.info(f"Deleted document {doc_id}")

        return True

    async def graph_query(self, cypher: str) -> Any:
        """
        Execute a graph query (delegated to graph.py).

        Args:
            cypher: Cypher-like query string

        Returns:
            Query results
        """
        # This will be implemented in graph.py
        from .graph import GraphOperations

        graph_ops = GraphOperations(self)
        return await graph_ops.execute_query(cypher)

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector database.

        Returns:
            Dict with statistics
        """
        if not self._initialized:
            await self.initialize()

        return {
            "total_documents": len(self._documents),
            "index_size": self._index.get_current_count() if self._index else 0,
            "embedding_dimension": self._embedder.embedding_dimension,
            "embedding_model": self.embedding_model,
            "index_params": self.index_params,
        }

    async def close(self) -> None:
        """Close connections and cleanup resources."""
        if self._embedder:
            await self._embedder.close()
        self._initialized = False
        logger.info("RuVectorClient closed")

    def __repr__(self) -> str:
        return (
            f"RuVectorClient(data_dir={self.data_dir}, "
            f"documents={len(self._documents)}, "
            f"model={self.embedding_model})"
        )


async def create_client(
    data_dir: Union[str, Path],
    embedding_model: str = "all-MiniLM-L6-v2",
    redis_url: Optional[str] = None,
) -> RuVectorClient:
    """
    Factory function to create and initialize a RuVectorClient.

    Args:
        data_dir: Directory for storing vector data
        embedding_model: Sentence-transformers model name
        redis_url: Redis URL for caching

    Returns:
        Initialized RuVectorClient
    """
    client = RuVectorClient(
        data_dir=data_dir,
        embedding_model=embedding_model,
        redis_url=redis_url,
    )
    await client.initialize()
    return client
