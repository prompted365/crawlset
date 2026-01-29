"""
Quick integration test for RuVector components.

This script verifies that all RuVector modules are properly integrated
and can be imported without errors.
"""
import asyncio
import sys
from pathlib import Path


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
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


async def test_basic_functionality():
    """Test basic functionality of RuVector components."""
    print("\nTesting basic functionality...")

    try:
        from ruvector import create_client, create_search_engine, create_graph

        # Create client with temporary directory
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            print(f"  Using temp directory: {tmpdir}")

            # Initialize client
            print("  Creating client...")
            client = await create_client(
                data_dir=tmpdir,
                embedding_model="all-MiniLM-L6-v2",
            )
            print("  ✓ Client created")

            # Insert test documents
            print("  Inserting test documents...")
            await client.insert_document(
                doc_id="doc1",
                text="This is a test document about artificial intelligence.",
                metadata={"category": "test"},
            )
            await client.insert_document(
                doc_id="doc2",
                text="Machine learning is a subset of artificial intelligence.",
                metadata={"category": "test"},
            )
            await client.insert_document(
                doc_id="doc3",
                text="Python is a popular programming language.",
                metadata={"category": "programming"},
            )
            print("  ✓ Documents inserted")

            # Test search
            print("  Testing search...")
            results = await client.hybrid_search("artificial intelligence", top_k=2)
            print(f"  ✓ Search returned {len(results)} results")

            # Test hybrid search engine
            print("  Creating hybrid search engine...")
            search_engine = await create_search_engine(client, alpha=0.5)
            results = await search_engine.search("machine learning", top_k=2)
            print(f"  ✓ Hybrid search returned {len(results)} results")

            # Test graph operations
            print("  Creating graph...")
            graph = await create_graph(client)
            await graph.build_graph_from_documents(similarity_threshold=0.5)
            stats = await graph.get_graph_stats()
            print(f"  ✓ Graph built: {stats['num_nodes']} nodes, {stats['num_edges']} edges")

            # Get stats
            print("  Getting client stats...")
            stats = await client.get_stats()
            print(f"  ✓ Stats: {stats['total_documents']} documents")

            # Cleanup
            await client.close()
            print("  ✓ Client closed")

        print("\n✓ All tests passed!")
        return True

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("RuVector Integration Test")
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
