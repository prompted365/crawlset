"""
RuVector HTTP Client for the Rust-based vector database service.

Communicates with the RuVector Axum server via async HTTP (httpx).
Provides HNSW vector indexing, GNN self-learning, SONA optimization,
and Cypher-like graph queries.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


class RuVectorClient:
    """
    Async HTTP client for the RuVector Rust service.

    Replaces the previous in-process hnswlib implementation with
    HTTP calls to the standalone Rust/Axum RuVector server.

    Features:
    - HNSW vector indexing (sub-millisecond search)
    - GNN self-learning layers
    - SONA optimization
    - Cypher-like graph queries
    - 61us p50 latency
    """

    def __init__(
        self,
        ruvector_url: Optional[str] = None,
        data_dir: Optional[Union[str, Path]] = None,
        collection: str = "crawlset",
        timeout: float = 30.0,
        **kwargs,
    ):
        """
        Initialize RuVector HTTP client.

        Args:
            ruvector_url: Base URL of the RuVector service (e.g. http://ruvector:6333).
                          Falls back to RUVECTOR_URL env var, then http://localhost:6333.
            data_dir: Unused, kept for backward compatibility with old constructor.
            collection: Default collection name.
            timeout: HTTP request timeout in seconds.
            **kwargs: Ignored (backward compatibility for embedding_model, redis_url, etc.)
        """
        self._base_url = (
            ruvector_url
            or os.environ.get("RUVECTOR_URL")
            or "http://localhost:6333"
        )
        self._collection = collection
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._initialized = False

        logger.info(f"RuVectorClient configured for {self._base_url}")

    async def initialize(self) -> None:
        """Initialize the HTTP client and ensure the default collection exists."""
        if self._initialized:
            return

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
        )

        # Ensure the default collection exists
        await self._ensure_collection(self._collection)
        self._initialized = True
        logger.info(f"RuVectorClient initialized (url={self._base_url})")

    async def _ensure_collection(self, name: str, dimension: int = 384) -> None:
        """Create collection if it doesn't already exist."""
        try:
            resp = await self._client.get(f"/collections/{name}")
            if resp.status_code == 200:
                return
        except Exception:
            pass

        try:
            await self._client.post(
                "/collections",
                json={"name": name, "dimension": dimension},
            )
            logger.info(f"Created collection: {name}")
        except Exception as e:
            logger.warning(f"Could not create collection {name}: {e}")

    async def _ensure_ready(self) -> None:
        """Ensure client is initialized before making requests."""
        if not self._initialized:
            await self.initialize()

    # ========================================================================
    # Document Operations
    # ========================================================================

    async def insert_document(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> str:
        """
        Insert a document into RuVector.

        Args:
            doc_id: Unique document ID.
            text: Document text content.
            metadata: Optional metadata dict.
            embedding: Pre-computed embedding vector. If not provided,
                       a zero vector placeholder is used (caller should
                       compute embeddings via embedder.py).

        Returns:
            Inserted document ID.
        """
        await self._ensure_ready()

        # If no embedding provided, create a zero vector as placeholder.
        if embedding is None:
            embedding = [0.0] * 384

        # Convert numpy arrays to lists if needed
        if hasattr(embedding, "tolist"):
            embedding = embedding.tolist()

        payload = {
            "id": doc_id,
            "text": text,
            "metadata": metadata or {},
            "embedding": embedding,
            "collection": self._collection,
        }

        resp = await self._client.post("/documents", json=payload)
        resp.raise_for_status()
        return doc_id

    async def bulk_insert(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 32,
    ) -> List[str]:
        """
        Bulk insert documents into RuVector.

        Args:
            documents: List of dicts with keys: id, text, metadata, embedding.
            batch_size: Ignored (kept for backward compatibility).

        Returns:
            List of inserted document IDs.
        """
        await self._ensure_ready()

        if not documents:
            return []

        logger.info(f"Bulk inserting {len(documents)} documents")

        doc_list = []
        for doc in documents:
            emb = doc.get("embedding", [0.0] * 384)
            if hasattr(emb, "tolist"):
                emb = emb.tolist()
            doc_list.append({
                "id": doc.get("id"),
                "text": doc.get("text", ""),
                "metadata": doc.get("metadata", {}),
                "embedding": emb,
            })

        payload = {
            "documents": doc_list,
            "collection": self._collection,
        }

        resp = await self._client.post("/documents/bulk", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("ids", [])

    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by ID.

        Args:
            doc_id: Document ID.

        Returns:
            Document dict or None if not found.
        """
        await self._ensure_ready()

        resp = await self._client.get(f"/documents/{doc_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document by ID.

        Args:
            doc_id: Document ID.

        Returns:
            True if deleted, False if not found.
        """
        await self._ensure_ready()

        resp = await self._client.delete(f"/documents/{doc_id}")
        return resp.status_code == 204

    # ========================================================================
    # Search
    # ========================================================================

    async def hybrid_search(
        self,
        query: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute vector similarity search against RuVector.

        Args:
            query: Text query (unused directly by Rust service; caller should
                   embed it first and pass the embedding).
            embedding: Query embedding vector.
            top_k: Number of results to return.
            filter_metadata: Optional metadata filter.

        Returns:
            List of search result dicts with id, text, metadata, score.
        """
        await self._ensure_ready()

        if embedding is None:
            embedding = [0.0] * 384

        if hasattr(embedding, "tolist"):
            embedding = embedding.tolist()

        payload = {
            "embedding": embedding,
            "top_k": top_k,
            "collection": self._collection,
        }
        if filter_metadata:
            payload["filter_metadata"] = filter_metadata

        resp = await self._client.post("/search", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])

    # ========================================================================
    # Graph Operations
    # ========================================================================

    async def graph_query(self, cypher: str) -> Dict[str, Any]:
        """
        Execute a Cypher-like graph query against RuVector.

        Args:
            cypher: Cypher query string.

        Returns:
            Query results dict.
        """
        await self._ensure_ready()

        resp = await self._client.post("/graph/query", json={"cypher": cypher})
        resp.raise_for_status()
        return resp.json()

    async def build_graph(
        self,
        similarity_threshold: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Build a graph from documents based on embedding similarity.

        Args:
            similarity_threshold: Minimum cosine similarity for edge creation.

        Returns:
            Dict with node and edge counts.
        """
        await self._ensure_ready()

        resp = await self._client.post(
            "/graph/build",
            json={
                "similarity_threshold": similarity_threshold,
                "collection": self._collection,
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
    ) -> Optional[List[str]]:
        """
        Find shortest path between two nodes.

        Args:
            source_id: Source node ID.
            target_id: Target node ID.
            max_depth: Maximum path depth.

        Returns:
            List of node IDs in the path, or None if no path found.
        """
        await self._ensure_ready()

        resp = await self._client.post(
            "/graph/path",
            json={
                "source_id": source_id,
                "target_id": target_id,
                "max_depth": max_depth,
            },
        )
        resp.raise_for_status()
        return resp.json().get("path")

    async def find_clusters(self) -> List[List[str]]:
        """
        Find document clusters based on graph structure.

        Returns:
            List of clusters (each cluster is a list of document IDs).
        """
        await self._ensure_ready()

        resp = await self._client.get("/graph/clusters")
        resp.raise_for_status()
        return resp.json().get("clusters", [])

    async def get_neighbors(
        self,
        node_id: str,
        edge_type: Optional[str] = None,
        max_depth: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Get neighbors of a node.

        Args:
            node_id: Node ID.
            edge_type: Optional edge type filter.
            max_depth: Maximum traversal depth.

        Returns:
            List of neighbor dicts.
        """
        await self._ensure_ready()

        params = {"max_depth": max_depth}
        if edge_type:
            params["edge_type"] = edge_type

        resp = await self._client.get(f"/graph/neighbors/{node_id}", params=params)
        resp.raise_for_status()
        return resp.json().get("neighbors", [])

    async def get_graph_stats(self) -> Dict[str, Any]:
        """
        Get graph statistics.

        Returns:
            Dict with num_nodes and num_edges.
        """
        await self._ensure_ready()

        resp = await self._client.get("/graph/stats")
        resp.raise_for_status()
        return resp.json()

    # ========================================================================
    # SONA & GNN (Operation Torque)
    # ========================================================================

    async def send_sona_trajectory(
        self, trajectory: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send a SONA learning trajectory to RuVector.

        After successful extraction jobs, send trajectory data so
        RuVector learns which extraction patterns work best.

        Args:
            trajectory: Trajectory data dict.

        Returns:
            Response with acceptance status.
        """
        await self._ensure_ready()

        resp = await self._client.post(
            "/sona/trajectory",
            json={"trajectory": trajectory},
        )
        resp.raise_for_status()
        return resp.json()

    async def train_gnn(
        self, interactions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Send query-result interaction data for GNN training.

        Background Celery task sends query-result interaction data
        so search results improve over time (+12.4% recall after 10K queries).

        Args:
            interactions: List of interaction dicts.

        Returns:
            Training status response.
        """
        await self._ensure_ready()

        resp = await self._client.post(
            "/gnn/train",
            json={"interactions": interactions},
        )
        resp.raise_for_status()
        return resp.json()

    # ========================================================================
    # Stats & Lifecycle
    # ========================================================================

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get RuVector service statistics.

        Returns:
            Dict with total_documents, collections, graph stats, etc.
        """
        await self._ensure_ready()

        resp = await self._client.get("/stats")
        resp.raise_for_status()
        return resp.json()

    async def health_check(self) -> Dict[str, Any]:
        """
        Check RuVector service health.

        Returns:
            Health status dict.
        """
        await self._ensure_ready()

        resp = await self._client.get("/health")
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            self._initialized = False
            logger.info("RuVectorClient closed")

    def __repr__(self) -> str:
        return f"RuVectorClient(url={self._base_url}, collection={self._collection})"


async def create_client(
    ruvector_url: Optional[str] = None,
    data_dir: Optional[Union[str, Path]] = None,
    collection: str = "crawlset",
    **kwargs,
) -> RuVectorClient:
    """
    Factory function to create and initialize a RuVectorClient.

    Args:
        ruvector_url: Base URL of the RuVector service.
        data_dir: Unused, kept for backward compatibility.
        collection: Default collection name.
        **kwargs: Additional keyword args (ignored for compatibility).

    Returns:
        Initialized RuVectorClient.
    """
    client = RuVectorClient(
        ruvector_url=ruvector_url,
        data_dir=data_dir,
        collection=collection,
    )
    await client.initialize()
    return client
