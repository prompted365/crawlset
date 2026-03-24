"""
RuVector - Rust-Based Vector Database Integration for Crawlset.

Communicates with the RuVector Rust/Axum service via async HTTP (httpx).
Provides HNSW vector indexing, GNN self-learning, SONA optimization,
Cypher-like graph queries, and hybrid search (BM25 + semantic).

Components:
- RuVectorClient: Async HTTP client for the RuVector Rust service
- EmbeddingGenerator: Sentence-transformers with Redis caching (Python-side)
- HybridSearchEngine: Combined lexical + semantic search
- GraphOperations: Delegates to RuVector Rust graph endpoints

Architecture:
    FastAPI Backend  ──httpx async──>  RuVector (Rust/Axum)
    Python 3.11                        HNSW + GNN + SONA
                                       Cypher Graph Queries
                                       61us p50 latency

Usage:
    from ruvector import create_client, create_search_engine

    # Create and initialize client (connects to Rust service)
    client = await create_client(ruvector_url="http://ruvector:6333")

    # Insert documents
    await client.insert_document(
        doc_id="doc1",
        text="Example document text",
        metadata={"source": "web", "url": "https://example.com"},
        embedding=[0.1, 0.2, ...]  # pre-computed via embedder.py
    )

    # Search
    results = await client.hybrid_search(embedding=[...], top_k=10)

    # Use hybrid search engine
    search_engine = await create_search_engine(client, alpha=0.5)
    results = await search_engine.search("query", top_k=10)

    # Graph operations
    from ruvector.graph import create_graph
    graph = await create_graph(client)
    await graph.build_graph_from_documents()
    clusters = await graph.find_clusters()

    # SONA & GNN (Operation Torque)
    await client.send_sona_trajectory({"pattern": "...", "success": True})
    await client.train_gnn([{"query": "...", "clicked": "doc1"}])

    # Cleanup
    await client.close()
"""

# Only the HTTP client is exported at package level.
# embedder, search, and graph all require numpy/sentence-transformers.
# Import those sub-modules directly in code that runs in worker images.
from .client import RuVectorClient, create_client

__all__ = [
    "RuVectorClient",
    "create_client",
]

__version__ = "0.2.0"
