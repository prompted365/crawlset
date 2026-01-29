"""
RuVector integration for the intelligence pipeline.

Provides vector database capabilities with hybrid search, graph operations,
and automatic embedding generation.

Main Components:
- RuVectorClient: Core client for document storage and retrieval
- EmbeddingGenerator: Text embedding with caching
- HybridSearchEngine: Combined lexical and semantic search
- GraphOperations: Knowledge graph features

Example usage:

    from ruvector import create_client, create_search_engine

    # Create and initialize client
    client = await create_client(
        data_dir="./data/ruvector",
        embedding_model="all-MiniLM-L6-v2",
        redis_url="redis://localhost:6379/0"
    )

    # Insert documents
    await client.insert_document(
        doc_id="doc1",
        text="Example document text",
        metadata={"source": "web", "url": "https://example.com"}
    )

    # Search
    results = await client.hybrid_search("query text", top_k=10)

    # Use hybrid search engine
    search_engine = await create_search_engine(client, alpha=0.5)
    results = await search_engine.search("query", top_k=10)

    # Graph operations
    from ruvector.graph import create_graph
    graph = await create_graph(client)
    await graph.build_graph_from_documents()
    clusters = await graph.find_clusters()

    # Cleanup
    await client.close()
"""

from .client import RuVectorClient, create_client
from .embedder import EmbeddingGenerator, create_embedder
from .graph import GraphEdge, GraphNode, GraphOperations, create_graph
from .search import BM25, HybridSearchEngine, create_search_engine

__all__ = [
    # Client
    "RuVectorClient",
    "create_client",
    # Embedder
    "EmbeddingGenerator",
    "create_embedder",
    # Search
    "HybridSearchEngine",
    "BM25",
    "create_search_engine",
    # Graph
    "GraphOperations",
    "GraphNode",
    "GraphEdge",
    "create_graph",
]

__version__ = "0.1.0"
