import asyncio
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

async def test_milvus():
    try:
        # Connect to Milvus
        connections.connect(host="localhost", port="19530")
        print("✓ Connected to Milvus")

        # List collections
        collections = utility.list_collections()
        print(f"✓ Found {len(collections)} collections: {collections}")

        # Create a test collection
        test_collection_name = "test_crawlset"

        # Drop if exists
        if test_collection_name in collections:
            utility.drop_collection(test_collection_name)
            print(f"✓ Dropped existing collection: {test_collection_name}")

        # Define schema
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=200, is_primary=True),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
        ]
        schema = CollectionSchema(fields=fields, description="Test collection")

        # Create collection
        collection = Collection(name=test_collection_name, schema=schema)
        print(f"✓ Created collection: {test_collection_name}")

        # Create index
        index_params = {
            "metric_type": "COSINE",
            "index_type": "HNSW",
            "params": {"M": 16, "efConstruction": 200}
        }
        collection.create_index(field_name="embedding", index_params=index_params)
        print("✓ Created HNSW index")

        # Insert test data
        import numpy as np
        test_data = [
            ["doc1", "doc2", "doc3"],  # IDs
            [np.random.rand(384).tolist() for _ in range(3)],  # Embeddings
            ["Test document 1", "Test document 2", "Test document 3"],  # Text
        ]
        collection.insert(test_data)
        collection.flush()
        print(f"✓ Inserted 3 test documents")

        # Load collection for search
        collection.load()
        print("✓ Loaded collection for search")

        # Perform search
        search_params = {"metric_type": "COSINE", "params": {"ef": 64}}
        query_vector = [np.random.rand(384).tolist()]
        results = collection.search(
            data=query_vector,
            anns_field="embedding",
            param=search_params,
            limit=2,
            output_fields=["text"]
        )
        print(f"✓ Search returned {len(results[0])} results")

        # Cleanup
        utility.drop_collection(test_collection_name)
        print(f"✓ Cleaned up test collection")

        connections.disconnect("default")
        print("\n✅ All Milvus integration tests passed!")

    except Exception as e:
        print(f"\n❌ Milvus test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_milvus())
