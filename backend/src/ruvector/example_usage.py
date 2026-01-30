"""
Example usage of RuVector integration with the intelligence pipeline.

This demonstrates how to integrate with the RuVector Rust service via HTTP.
Requires the RuVector service running at RUVECTOR_URL (default: http://localhost:6333).
"""
import asyncio
import os

from .client import RuVectorClient


async def example_basic_operations():
    """Example: Basic document operations."""
    print("=" * 60)
    print("Example 1: Basic Document Operations")
    print("=" * 60)

    # Create client (connects to RuVector Rust service via HTTP)
    client = RuVectorClient(
        ruvector_url=os.environ.get("RUVECTOR_URL", "http://localhost:6333"),
    )
    await client.initialize()

    # Insert documents
    print("\nInserting documents...")
    await client.insert_document(
        doc_id="doc1",
        text="Artificial intelligence and machine learning are transforming technology.",
        metadata={"source": "article", "category": "tech"},
    )

    await client.insert_document(
        doc_id="doc2",
        text="Deep learning is a subset of machine learning using neural networks.",
        metadata={"source": "blog", "category": "tech"},
    )

    await client.insert_document(
        doc_id="doc3",
        text="Python is widely used in data science and AI applications.",
        metadata={"source": "tutorial", "category": "programming"},
    )

    print("Documents inserted")

    # Search
    print("\nSearching for 'machine learning'...")
    results = await client.hybrid_search("machine learning", top_k=2)

    for i, result in enumerate(results, 1):
        print(f"\n{i}. Score: {result['score']:.3f}")
        print(f"   Text: {result['text']}")
        print(f"   Metadata: {result['metadata']}")

    # Get stats
    stats = await client.get_stats()
    print(f"\nClient stats: {stats}")

    await client.close()


async def example_bulk_insert_and_search():
    """Example: Bulk insert with hybrid search."""
    print("\n" + "=" * 60)
    print("Example 2: Bulk Insert and Hybrid Search")
    print("=" * 60)

    client = RuVectorClient()
    await client.initialize()

    # Bulk insert
    documents = [
        {
            "id": f"article_{i}",
            "text": f"Article {i} about technology and innovation.",
            "metadata": {"type": "article", "index": i},
        }
        for i in range(10)
    ]

    print(f"\nBulk inserting {len(documents)} documents...")
    doc_ids = await client.bulk_insert(documents, batch_size=5)
    print(f"Inserted {len(doc_ids)} documents")

    # Search
    results = await client.hybrid_search("technology", top_k=3)
    print("\nSearch results:")
    for result in results:
        print(f"  - {result['id']}: {result['score']:.3f}")

    await client.close()


async def example_graph_operations():
    """Example: Graph operations and clustering."""
    print("\n" + "=" * 60)
    print("Example 3: Graph Operations")
    print("=" * 60)

    client = RuVectorClient()
    await client.initialize()

    # Insert some documents
    documents = [
        {"id": "ai1", "text": "Artificial intelligence and machine learning", "metadata": {}},
        {"id": "ai2", "text": "Deep learning and neural networks", "metadata": {}},
        {"id": "ai3", "text": "Natural language processing with AI", "metadata": {}},
        {"id": "web1", "text": "Web development with Python and JavaScript", "metadata": {}},
        {"id": "web2", "text": "Frontend frameworks React and Vue", "metadata": {}},
    ]

    await client.bulk_insert(documents)

    # Build graph via RuVector Rust service
    print("\nBuilding knowledge graph...")
    await client.build_graph(similarity_threshold=0.5)

    # Find path
    print("\nFinding path between ai1 and ai3...")
    path = await client.find_path("ai1", "ai3", max_depth=3)
    if path:
        print(f"Path found: {' -> '.join(path)}")
    else:
        print("No path found")

    # Get neighbors
    print("\nGetting neighbors of ai1...")
    neighbors = await client.get_neighbors("ai1")
    for neighbor in neighbors:
        print(f"  - {neighbor}")

    # Find clusters
    print("\nFinding document clusters...")
    clusters = await client.find_clusters()
    for i, cluster in enumerate(clusters):
        print(f"  Cluster {i}: {cluster}")

    await client.close()


async def example_webset_integration():
    """Example: Integration with websets."""
    print("\n" + "=" * 60)
    print("Example 4: Webset Integration")
    print("=" * 60)

    client = RuVectorClient()
    await client.initialize()

    # Simulate webset items
    webset_id = "webset_123"
    webset_items = [
        {
            "id": f"{webset_id}_item1",
            "text": "Article about AI in healthcare",
            "metadata": {
                "webset_id": webset_id,
                "url": "https://example.com/ai-healthcare",
                "title": "AI in Healthcare",
            },
        },
        {
            "id": f"{webset_id}_item2",
            "text": "Machine learning for medical diagnosis",
            "metadata": {
                "webset_id": webset_id,
                "url": "https://example.com/ml-diagnosis",
                "title": "ML in Medicine",
            },
        },
        {
            "id": f"{webset_id}_item3",
            "text": "Deep learning for drug discovery",
            "metadata": {
                "webset_id": webset_id,
                "url": "https://example.com/dl-drugs",
                "title": "DL Drug Discovery",
            },
        },
    ]

    print(f"\nInserting webset items for {webset_id}...")
    await client.bulk_insert(webset_items)

    # Search within webset
    print("\nSearching within webset...")
    results = await client.hybrid_search(
        query="medical AI applications",
        top_k=5,
    )

    print(f"\nFound {len(results)} results:")
    for result in results:
        print(f"\n  Title: {result.get('metadata', {}).get('title', 'N/A')}")
        print(f"  Score: {result['score']:.3f}")
        print(f"  Text: {result.get('text', '')[:100]}...")

    await client.close()


async def example_sona_and_gnn():
    """Example: SONA self-learning and GNN training."""
    print("\n" + "=" * 60)
    print("Example 5: SONA + GNN Self-Learning")
    print("=" * 60)

    client = RuVectorClient()
    await client.initialize()

    # Send SONA trajectory after successful extraction
    print("\nSending SONA trajectory...")
    trajectory_result = await client.send_sona_trajectory(
        actions=[
            {"type": "fetch", "url": "https://example.com", "success": True},
            {"type": "parse", "parser": "trafilatura", "success": True},
            {"type": "enrich", "plugin": "content_enricher", "success": True},
        ],
        reward=0.92,
    )
    print(f"SONA response: {trajectory_result}")

    # Train GNN with query-result interactions
    print("\nTraining GNN with interactions...")
    gnn_result = await client.train_gnn(
        interactions=[
            {"query": "AI healthcare", "doc_id": "doc1", "relevance": 0.95},
            {"query": "machine learning", "doc_id": "doc2", "relevance": 0.87},
            {"query": "deep learning", "doc_id": "doc3", "relevance": 0.72},
        ],
    )
    print(f"GNN response: {gnn_result}")

    await client.close()


async def main():
    """Run all examples."""
    print("\nRuVector Integration Examples")
    print("(Requires RuVector Rust service running)")
    print("==============================\n")

    try:
        await example_basic_operations()
        await example_bulk_insert_and_search()
        await example_graph_operations()
        await example_webset_integration()
        await example_sona_and_gnn()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
