"""
Quick integration test for RuVector components.

Tests the RuVector Rust service via the async HTTP client, including
document operations, search, graph, SONA, and GNN endpoints.
"""
import asyncio
import os
import sys


async def test_imports():
    """Test that all modules can be imported."""
    print("Testing RuVector imports...")

    try:
        from ruvector import (
            RuVectorClient,
            create_client,
            EmbeddingGenerator,
            create_embedder,
            HybridSearchEngine,
            create_search_engine,
            GraphOperations,
            create_graph,
        )
        print("  All imports successful")
        return True
    except ImportError as e:
        print(f"  Import error: {e}")
        return False


async def test_basic_functionality():
    """Test basic functionality against the RuVector Rust service."""
    print("\nTesting basic functionality...")

    try:
        from ruvector import create_client, create_search_engine, create_graph

        ruvector_url = os.environ.get("RUVECTOR_URL", "http://localhost:6333")
        print(f"  Connecting to RuVector at: {ruvector_url}")

        # Initialize client
        print("  Creating client...")
        client = await create_client(ruvector_url=ruvector_url)
        print("  Client created")

        # Health check
        print("  Checking health...")
        health = await client.health_check()
        print(f"  Health: {health['status']}")

        # Insert test documents with dummy embeddings
        print("  Inserting test documents...")
        import numpy as np

        for doc_id, text in [
            ("doc1", "This is a test document about artificial intelligence."),
            ("doc2", "Machine learning is a subset of artificial intelligence."),
            ("doc3", "Python is a popular programming language."),
        ]:
            embedding = np.random.rand(384).tolist()
            await client.insert_document(
                doc_id=doc_id,
                text=text,
                metadata={"category": "test"},
                embedding=embedding,
            )
        print("  Documents inserted")

        # Test search
        print("  Testing search...")
        query_embedding = np.random.rand(384).tolist()
        results = await client.hybrid_search(embedding=query_embedding, top_k=2)
        print(f"  Search returned {len(results)} results")

        # Test graph operations
        print("  Building graph...")
        graph_result = await client.build_graph(similarity_threshold=0.0)
        print(f"  Graph: {graph_result.get('nodes', 0)} nodes, {graph_result.get('edges', 0)} edges")

        # Test graph stats
        graph_stats = await client.get_graph_stats()
        print(f"  Graph stats: {graph_stats}")

        # Test SONA trajectory
        print("  Testing SONA trajectory...")
        sona_result = await client.send_sona_trajectory({
            "pattern": "test_extraction",
            "success": True,
            "confidence": 0.95,
        })
        print(f"  SONA: {sona_result.get('status', 'unknown')}")

        # Test GNN training
        print("  Testing GNN training...")
        gnn_result = await client.train_gnn([
            {"query": "AI research", "clicked": "doc1", "position": 1},
        ])
        print(f"  GNN: {gnn_result.get('status', 'unknown')}")

        # Get stats
        print("  Getting client stats...")
        stats = await client.get_stats()
        print(f"  Stats: {stats.get('total_documents', 0)} documents")

        # Cleanup
        for doc_id in ["doc1", "doc2", "doc3"]:
            await client.delete_document(doc_id)
        await client.close()
        print("  Client closed")

        print("\n  All tests passed!")
        return True

    except Exception as e:
        print(f"\n  Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("RuVector Integration Test (Rust HTTP Service)")
    print("=" * 60)

    # Test imports
    imports_ok = await test_imports()
    if not imports_ok:
        sys.exit(1)

    # Test functionality
    functionality_ok = await test_basic_functionality()
    if not functionality_ok:
        sys.exit(1)

    print("\n" + "=" * 60)
    print("All tests completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
