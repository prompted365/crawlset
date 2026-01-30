# Milvus Integration Guide (Deprecated)

> **This guide is deprecated.** Crawlset has migrated from the 3-service Milvus stack (etcd + MinIO + standalone) to **RuVector**, a single Rust-based vector database service with HNSW indexing, GNN self-learning, SONA optimization, and Cypher graph queries.

## Migration

See the following resources for the new RuVector integration:

- **[RuVector Integration Guide](RUVECTOR_INTEGRATION.md)** - Deep dive into RuVector capabilities
- **[RuVector README](../backend/src/ruvector/README.md)** - Python client API reference
- **[Migration Guide](../backend/src/ruvector/MIGRATION_GUIDE.md)** - Step-by-step migration from Milvus

## What Changed

| Before | After |
|--------|-------|
| 3-service Milvus stack (etcd + MinIO + standalone) | 1 RuVector Rust service |
| In-process hnswlib Python library | HTTP client (`httpx`) to Rust/Axum |
| `pymilvus` + `hnswlib` + `marshmallow` dependencies | `httpx` (already in requirements) |
| `milvus_doc_id` field in database | `ruvector_doc_id` field in database |
| Millisecond search latency | 61us p50 latency |

## Quick Start (New)

```python
from src.ruvector.client import RuVectorClient

client = RuVectorClient(ruvector_url="http://localhost:6333")
await client.initialize()

# Insert document
await client.insert_document(
    doc_id="doc1",
    text="Your document text here",
    metadata={"source": "web"}
)

# Search
results = await client.hybrid_search("query text", top_k=10)

await client.close()
```

See the [RuVector Integration Guide](RUVECTOR_INTEGRATION.md) for full documentation.
