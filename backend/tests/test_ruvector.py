"""
RuVector integration tests.

Tests the RuVector Rust service via the Python HTTP client.
Requires the RuVector Rust service running at RUVECTOR_URL.
"""
import asyncio
import os


async def test_ruvector():
    """Test RuVector service connectivity and basic operations."""
    try:
        from src.ruvector.client import RuVectorClient

        ruvector_url = os.environ.get("RUVECTOR_URL", "http://localhost:6333")
        client = RuVectorClient(ruvector_url=ruvector_url)
        await client.initialize()
        print(f"Connected to RuVector at {ruvector_url}")

        # Health check
        health = await client.health_check()
        print(f"Health: {health}")
        assert health["status"] == "healthy"

        # Insert test documents
        import numpy as np

        for i in range(3):
            embedding = np.random.rand(384).tolist()
            await client.insert_document(
                doc_id=f"test_doc_{i}",
                text=f"Test document {i} about artificial intelligence.",
                metadata={"test": True, "index": i},
                embedding=embedding,
            )
        print("Inserted 3 test documents")

        # Search
        query_embedding = np.random.rand(384).tolist()
        results = await client.hybrid_search(embedding=query_embedding, top_k=2)
        print(f"Search returned {len(results)} results")
        assert len(results) <= 2

        # Get document
        doc = await client.get_document("test_doc_0")
        assert doc is not None
        print(f"Retrieved document: {doc['id']}")

        # Get stats
        stats = await client.get_stats()
        print(f"Stats: {stats}")
        assert stats["total_documents"] >= 3

        # Build graph
        graph_result = await client.build_graph(similarity_threshold=0.0)
        print(f"Graph: {graph_result}")

        # Graph stats
        graph_stats = await client.get_graph_stats()
        print(f"Graph stats: {graph_stats}")

        # Delete test documents
        for i in range(3):
            await client.delete_document(f"test_doc_{i}")
        print("Cleaned up test documents")

        await client.close()
        print("\nAll RuVector integration tests passed!")

    except Exception as e:
        print(f"\nRuVector test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_ruvector())
