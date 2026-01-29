"""
Example usage of RuVector integration with the intelligence pipeline.

This demonstrates how to integrate RuVector with websets, extractors,
and search functionality.
"""
import asyncio
from pathlib import Path

from ruvector import create_client, create_search_engine
from ruvector.graph import create_graph


async def example_basic_operations():
    """Example: Basic document operations."""
    print("=" * 60)
    print("Example 1: Basic Document Operations")
    print("=" * 60)

    # Create client
    client = await create_client(
        data_dir="./data/ruvector",
        embedding_model="all-MiniLM-L6-v2",
        redis_url="redis://localhost:6379/0",
    )

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

    print("✓ Documents inserted")

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

    client = await create_client(data_dir="./data/ruvector")

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
    print(f"✓ Inserted {len(doc_ids)} documents")

    # Create search engine
    print("\nCreating hybrid search engine...")
    search_engine = await create_search_engine(client, alpha=0.6)

    # Search with different alpha values
    for alpha in [0.0, 0.5, 1.0]:
        search_engine.set_alpha(alpha)
        results = await search_engine.search("technology", top_k=3)

        print(f"\nSearch results (alpha={alpha}):")
        for result in results:
            print(f"  - {result['id']}: {result['score']:.3f}")

    await client.close()


async def example_graph_operations():
    """Example: Graph operations and clustering."""
    print("\n" + "=" * 60)
    print("Example 3: Graph Operations")
    print("=" * 60)

    client = await create_client(data_dir="./data/ruvector")

    # Insert some documents
    documents = [
        {"id": "ai1", "text": "Artificial intelligence and machine learning", "metadata": {}},
        {"id": "ai2", "text": "Deep learning and neural networks", "metadata": {}},
        {"id": "ai3", "text": "Natural language processing with AI", "metadata": {}},
        {"id": "web1", "text": "Web development with Python and JavaScript", "metadata": {}},
        {"id": "web2", "text": "Frontend frameworks React and Vue", "metadata": {}},
    ]

    await client.bulk_insert(documents)

    # Create graph
    print("\nBuilding knowledge graph...")
    graph = await create_graph(client)
    await graph.build_graph_from_documents(similarity_threshold=0.5)

    stats = await graph.get_graph_stats()
    print(f"Graph stats: {stats}")

    # Find path
    print("\nFinding path between ai1 and ai3...")
    path = await graph.find_path("ai1", "ai3", max_depth=3)
    if path:
        print(f"Path found: {' -> '.join(path)}")
    else:
        print("No path found")

    # Get neighbors
    print("\nGetting neighbors of ai1...")
    neighbors = await graph.get_neighbors("ai1", max_depth=1)
    for neighbor in neighbors:
        print(f"  - {neighbor['id']}: {neighbor['edge_properties']}")

    # Find clusters
    print("\nFinding document clusters...")
    clusters = await graph.find_clusters(eps=0.4, min_samples=2)
    for i, cluster in enumerate(clusters):
        print(f"  Cluster {i}: {cluster}")

    # Export graph
    graph_data = await graph.export_graph(format="json")
    print(f"\nGraph exported: {len(graph_data['nodes'])} nodes, {len(graph_data['edges'])} edges")

    await client.close()


async def example_webset_integration():
    """Example: Integration with websets."""
    print("\n" + "=" * 60)
    print("Example 4: Webset Integration")
    print("=" * 60)

    client = await create_client(data_dir="./data/ruvector")

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
    search_engine = await create_search_engine(client, alpha=0.7)
    results = await search_engine.search(
        query="medical AI applications",
        top_k=5,
        filter_metadata={"webset_id": webset_id},
    )

    print(f"\nFound {len(results)} results in webset {webset_id}:")
    for result in results:
        print(f"\n  Title: {result['metadata']['title']}")
        print(f"  URL: {result['metadata']['url']}")
        print(f"  Score: {result['score']:.3f}")
        print(f"  Text: {result['text'][:100]}...")

    await client.close()


async def example_chunking_and_embedding():
    """Example: Text chunking and embedding."""
    print("\n" + "=" * 60)
    print("Example 5: Text Chunking and Embedding")
    print("=" * 60)

    client = await create_client(data_dir="./data/ruvector")

    # Long document
    long_text = " ".join([
        f"This is sentence {i} in a very long document about various topics."
        for i in range(100)
    ])

    print(f"\nOriginal text length: {len(long_text)} chars")
    print(f"Token count: {client._embedder.count_tokens(long_text)}")

    # Chunk text
    chunks = client._embedder.chunk_text(long_text, max_tokens=50, overlap=10)
    print(f"\nSplit into {len(chunks)} chunks")

    # Insert chunks
    print("\nInserting chunks...")
    for i, chunk in enumerate(chunks):
        await client.insert_document(
            doc_id=f"doc_chunk_{i}",
            text=chunk,
            metadata={"chunk_index": i, "total_chunks": len(chunks)},
        )

    print(f"✓ Inserted {len(chunks)} chunks")

    # Search across chunks
    results = await client.hybrid_search("sentence 50", top_k=3)
    print("\nSearch results:")
    for result in results:
        chunk_idx = result['metadata']['chunk_index']
        print(f"  Chunk {chunk_idx}: score={result['score']:.3f}")

    await client.close()


async def main():
    """Run all examples."""
    print("\nRuVector Integration Examples")
    print("==============================\n")

    try:
        await example_basic_operations()
        await example_bulk_insert_and_search()
        await example_graph_operations()
        await example_webset_integration()
        await example_chunking_and_embedding()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
