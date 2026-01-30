"""
RuVector integration tests.

Tests the RuVector Rust service via the Python HTTP client.
Requires the RuVector Rust service running at RUVECTOR_URL.
"""
import asyncio
import os

import pytest


RUVECTOR_URL = os.environ.get("RUVECTOR_URL", "http://localhost:6333")

# Skip the entire module when RuVector isn't reachable
pytestmark = pytest.mark.skipif(
    os.environ.get("RUVECTOR_LIVE") != "1",
    reason="RuVector live tests disabled (set RUVECTOR_LIVE=1 to enable)",
)


@pytest.mark.asyncio
async def test_ruvector_health():
    """Test RuVector service health endpoint."""
    from src.ruvector.client import RuVectorClient

    client = RuVectorClient(ruvector_url=RUVECTOR_URL)
    await client.initialize()

    health = await client.health_check()
    assert health["status"] == "healthy"

    await client.close()


@pytest.mark.asyncio
async def test_ruvector_insert_search_delete():
    """Test insert, search, and delete against a live RuVector service."""
    import numpy as np
    from src.ruvector.client import RuVectorClient

    client = RuVectorClient(ruvector_url=RUVECTOR_URL)
    await client.initialize()

    try:
        # Insert 3 documents
        for i in range(3):
            embedding = np.random.rand(384).tolist()
            await client.insert_document(
                doc_id=f"test_doc_{i}",
                text=f"Test document {i} about artificial intelligence.",
                metadata={"test": True, "index": i},
                embedding=embedding,
            )

        # Search
        query_embedding = np.random.rand(384).tolist()
        results = await client.hybrid_search(embedding=query_embedding, top_k=2)
        assert len(results) <= 2

        # Get document
        doc = await client.get_document("test_doc_0")
        assert doc is not None

        # Stats
        stats = await client.get_stats()
        assert stats["total_documents"] >= 3

        # Graph
        await client.build_graph(similarity_threshold=0.0)
        graph_stats = await client.get_graph_stats()
        assert graph_stats is not None

    finally:
        # Cleanup
        for i in range(3):
            try:
                await client.delete_document(f"test_doc_{i}")
            except Exception:
                pass
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_ruvector_insert_search_delete())
