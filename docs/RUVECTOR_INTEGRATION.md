# RuVector Integration Guide

**Crawlset's vector search layer powered by RuVector -- a Rust-based self-learning vector database.**

Designed by [Ruv](https://github.com/ruvnet) | Repository: [github.com/ruvnet/ruvector](https://github.com/ruvnet/ruvector)

---

## Overview

RuVector is the vector database backend for Crawlset. It replaces the traditional 3-service Milvus stack (etcd + MinIO + Milvus standalone) with a **single Rust/Axum service** that delivers sub-millisecond search latency, self-learning capabilities, and graph query support.

The Python backend communicates with RuVector via **async HTTP (httpx)** to the Rust/Axum server on port **6333**.

### Why RuVector?

| Metric | RuVector | Milvus | Qdrant |
|--------|----------|--------|--------|
| **p50 Latency** | 61us | ~5ms | ~2ms |
| **Memory (1M vectors)** | 200MB | ~2GB | ~1GB |
| **Services Required** | 1 (single binary) | 3 (etcd + MinIO + standalone) | 1 |
| **Self-Learning** | GNN + SONA | No | No |
| **Graph Queries** | Cypher | No | No |
| **Language** | Rust | Go + C++ | Rust |

---

## Core Capabilities

### 1. HNSW Indexing

RuVector uses Hierarchical Navigable Small World (HNSW) graphs for approximate nearest neighbor search. The HNSW index provides logarithmic search complexity with high recall.

**Configuration:**
```json
{
  "index_type": "hnsw",
  "params": {
    "m": 16,
    "ef_construction": 200,
    "ef_search": 100
  }
}
```

**Performance characteristics:**
- Sub-millisecond search latency (61us p50)
- 95%+ recall at default settings
- Incremental index updates (no full rebuilds)
- Concurrent read/write with lock-free data structures

### 2. GNN Self-Learning

Graph Neural Network layers sit on top of the HNSW index and learn from query patterns. Over time, the GNN adjusts edge weights in the HNSW graph to improve recall for frequently accessed regions of the vector space.

**How it works:**
1. Every search query is logged as a training signal
2. The GNN identifies clusters of related queries
3. Edge weights in the HNSW graph are adjusted to create shorter paths between frequently co-retrieved vectors
4. The learning is incremental and does not require downtime

**Configuration:**
```json
{
  "gnn": {
    "enabled": true,
    "learning_rate": 0.001,
    "training_interval_seconds": 300,
    "min_samples_before_training": 100
  }
}
```

**Impact on Crawlset:** Webset searches that are repeated (e.g., monitor refresh queries) get progressively faster and more accurate as the GNN learns the access patterns.

### 3. SONA Optimization

Self-Organizing Neural Architecture (SONA) dynamically adjusts index parameters based on workload characteristics. SONA monitors query latency, recall rates, and memory usage, then tunes parameters like `ef_search`, `m`, and shard distribution.

**Adaptive behaviors:**
- Increases `ef_search` for collections with diverse content (higher recall needed)
- Reduces `ef_search` for homogeneous collections (speed over recall)
- Adjusts shard placement based on access patterns
- Compacts unused regions of the index

**Configuration:**
```json
{
  "sona": {
    "enabled": true,
    "optimization_interval_seconds": 600,
    "target_latency_us": 100,
    "target_recall": 0.95
  }
}
```

### 4. Cypher Graph Queries

RuVector includes a built-in graph query engine that supports a subset of Cypher. This enables entity relationship traversal, clustering, and path finding directly in the vector database without a separate graph database.

**Example queries:**

```cypher
-- Find all documents related to a specific entity
MATCH (doc:Document)-[:MENTIONS]->(entity:Entity {name: "OpenAI"})
RETURN doc.title, doc.url

-- Find paths between two entities
MATCH path = (a:Entity {name: "GPT-4"})-[:RELATED_TO*1..3]->(b:Entity {name: "Transformer"})
RETURN path

-- Cluster analysis
MATCH (doc:Document)-[:SIMILAR_TO]->(neighbor:Document)
WHERE doc.webset_id = "webset_123"
RETURN doc.title, count(neighbor) AS connections
ORDER BY connections DESC
LIMIT 10
```

**Graph construction in Crawlset:** When content is extracted, the enrichment plugins identify entities and relationships. These are stored as graph edges in RuVector alongside the vector embeddings, enabling both semantic search and graph traversal in a single query.

---

## Architecture

### Single-Service Deployment

```
┌─────────────────────────────────────────┐
│              RuVector Service            │
│            (Rust/Axum :6333)             │
│                                          │
│  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │   HNSW   │  │   GNN    │  │  SONA  │ │
│  │  Index   │  │ Learning │  │ Tuning │ │
│  └──────────┘  └──────────┘  └────────┘ │
│  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │  Graph   │  │  BM25    │  │  REST  │ │
│  │  Engine  │  │  Index   │  │  API   │ │
│  └──────────┘  └──────────┘  └────────┘ │
│                                          │
│  Storage: /data/ruvector/                │
│  - *.hnsw (vector index files)           │
│  - *.graph (relationship edges)          │
│  - *.bm25 (keyword index)               │
│  - learned_patterns/ (GNN weights)       │
└─────────────────────────────────────────┘
```

This replaces the previous 3-service Milvus deployment:

```
BEFORE (Milvus):                    AFTER (RuVector):
┌─────────┐                         ┌──────────────┐
│  etcd   │                         │   RuVector   │
│ :2379   │                         │    :6333     │
├─────────┤        ───────>         │  (single     │
│  MinIO  │                         │   binary)    │
│ :9000   │                         └──────────────┘
├─────────┤
│ Milvus  │
│ :19530  │
└─────────┘
```

### Communication Pattern

The Python backend uses `httpx.AsyncClient` for all RuVector operations:

```python
# backend/src/ruvector/client.py
import httpx
from typing import Any

class RuVectorClient:
    """Async HTTP client for RuVector (Rust/Axum server on port 6333)."""

    def __init__(self, base_url: str = "http://localhost:6333"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=30.0)

    async def health(self) -> dict:
        resp = await self.client.get("/health")
        resp.raise_for_status()
        return resp.json()

    async def create_collection(self, name: str, dimension: int = 384) -> dict:
        resp = await self.client.post("/collections", json={
            "name": name,
            "dimension": dimension,
            "index_type": "hnsw",
            "enable_gnn": True,
            "enable_graph": True,
        })
        resp.raise_for_status()
        return resp.json()

    async def insert(
        self, collection: str, id: str, text: str, metadata: dict[str, Any]
    ) -> dict:
        resp = await self.client.post(f"/collections/{collection}/points", json={
            "id": id,
            "text": text,
            "metadata": metadata,
        })
        resp.raise_for_status()
        return resp.json()

    async def search(
        self,
        collection: str,
        query: str,
        top_k: int = 10,
        hybrid_alpha: float = 0.7,
        enable_gnn: bool = True,
    ) -> list[dict]:
        resp = await self.client.post(f"/collections/{collection}/search", json={
            "query": query,
            "top_k": top_k,
            "hybrid_alpha": hybrid_alpha,
            "enable_gnn": enable_gnn,
        })
        resp.raise_for_status()
        return resp.json()["results"]

    async def graph_query(self, cypher: str) -> list[dict]:
        resp = await self.client.post("/graph/query", json={
            "cypher": cypher,
        })
        resp.raise_for_status()
        return resp.json()["results"]

    async def delete(self, collection: str, id: str) -> dict:
        resp = await self.client.delete(f"/collections/{collection}/points/{id}")
        resp.raise_for_status()
        return resp.json()

    async def close(self):
        await self.client.aclose()
```

---

## How Crawlset Leverages RuVector

### Hybrid Search Pipeline

Crawlset's search combines three signals, all served by RuVector:

1. **BM25 Keyword Search** -- Traditional lexical matching for exact terms
2. **HNSW Vector Search** -- Semantic similarity via sentence-transformer embeddings
3. **GNN-Enhanced Reranking** -- Learned patterns boost frequently co-retrieved results

```python
# backend/src/ruvector/search.py
from src.ruvector.client import RuVectorClient

async def hybrid_search(
    client: RuVectorClient,
    collection: str,
    query: str,
    alpha: float = 0.7,
    top_k: int = 20,
) -> list[dict]:
    """
    Hybrid search combining BM25 + HNSW + GNN.

    Args:
        alpha: Weight for semantic vs lexical (0.7 = 70% semantic, 30% lexical)
    """
    results = await client.search(
        collection=collection,
        query=query,
        top_k=top_k,
        hybrid_alpha=alpha,
        enable_gnn=True,
    )
    return results
```

### Embedding Pipeline

```python
# backend/src/ruvector/embedder.py
from sentence_transformers import SentenceTransformer
import redis.asyncio as redis

class CachedEmbedder:
    """Generate embeddings with Redis caching."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.redis = redis.Redis()
        self.dimension = self.model.get_sentence_embedding_dimension()

    async def embed(self, text: str) -> list[float]:
        cache_key = f"embed:{hash(text)}"
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        embedding = self.model.encode(text).tolist()
        await self.redis.setex(cache_key, 3600, json.dumps(embedding))
        return embedding
```

### Graph Operations for Websets

Crawlset uses RuVector's graph engine to model relationships between extracted entities:

```python
# backend/src/ruvector/graph.py
from src.ruvector.client import RuVectorClient

async def find_related_entities(client: RuVectorClient, entity_name: str) -> list[dict]:
    """Find entities related to a given entity via graph traversal."""
    return await client.graph_query(
        f'MATCH (a:Entity {{name: "{entity_name}"}})-[:RELATED_TO]->(b) RETURN b'
    )

async def cluster_webset(client: RuVectorClient, webset_id: str) -> list[dict]:
    """Cluster documents in a webset by entity co-occurrence."""
    return await client.graph_query(
        f'MATCH (d:Document {{webset_id: "{webset_id}"}})-[:MENTIONS]->(e:Entity)'
        f' RETURN e.name, count(d) AS mentions ORDER BY mentions DESC'
    )

async def entity_path(
    client: RuVectorClient, entity_a: str, entity_b: str, max_hops: int = 3
) -> list[dict]:
    """Find shortest path between two entities."""
    return await client.graph_query(
        f'MATCH path = (a:Entity {{name: "{entity_a}"}})'
        f'-[:RELATED_TO*1..{max_hops}]->'
        f'(b:Entity {{name: "{entity_b}"}}) RETURN path'
    )
```

---

## Operation Torque Synergies

RuVector integrates with the broader Operation Torque ecosystem:

### Boris Parallel Processing

Boris agents can distribute large-scale embedding generation and index operations across multiple workers. When Crawlset triggers a batch extraction, Boris coordinates parallel inserts into RuVector:

```
Boris Agent Pool
    ├── Worker 1: Embed + Insert docs 1-1000
    ├── Worker 2: Embed + Insert docs 1001-2000
    └── Worker 3: Embed + Insert docs 2001-3000
         │
         └──> RuVector :6333 (concurrent writes, lock-free HNSW)
```

RuVector's lock-free HNSW implementation supports concurrent writes from multiple Boris workers without contention.

### Fusion Core Signals

Fusion Core signal processing can feed real-time intelligence signals into RuVector. As signals are detected (e.g., trending topic, breaking news, sentiment shift), they are embedded and inserted into a dedicated RuVector collection for rapid retrieval:

```python
# Example: Fusion Core signal ingestion
async def ingest_signal(client: RuVectorClient, signal: dict):
    await client.insert(
        collection="fusion_signals",
        id=signal["signal_id"],
        text=signal["content"],
        metadata={
            "signal_type": signal["type"],
            "confidence": signal["confidence"],
            "source": signal["source"],
            "timestamp": signal["timestamp"],
        },
    )
```

Crawlset monitors can then query across both webset content and Fusion Core signals for comprehensive intelligence:

```python
# Cross-collection search
webset_results = await client.search(collection="websets", query=query)
signal_results = await client.search(collection="fusion_signals", query=query)
# Merge and rerank
```

### SONA + Monitor Scheduling

SONA optimization aligns with Crawlset's monitor scheduling. When monitors run on a cron schedule (e.g., every 6 hours), SONA pre-tunes the index for the expected query pattern right before the scheduled execution window, minimizing latency during monitor runs.

---

## Performance Benchmarks

Benchmarks on a standard 4-core, 16GB RAM machine:

| Operation | Vectors | Latency (p50) | Latency (p99) | Throughput |
|-----------|---------|---------------|---------------|------------|
| Insert | 1 | 120us | 250us | 8,000/sec |
| Insert (batch 1000) | 1000 | 15ms | 25ms | 66,000/sec |
| Search (top-10) | 100K | 61us | 180us | 16,000 qps |
| Search (top-10) | 1M | 85us | 300us | 11,000 qps |
| Search (top-10) | 10M | 140us | 500us | 7,000 qps |
| Hybrid search | 1M | 200us | 600us | 5,000 qps |
| Graph query (1 hop) | 1M | 90us | 250us | 11,000 qps |
| Graph query (3 hops) | 1M | 350us | 1.2ms | 2,800 qps |

**Memory footprint:**
- 200MB per 1M vectors (384 dimensions, float32)
- Graph index adds ~50MB per 1M entities
- BM25 index adds ~100MB per 1M documents
- GNN learned weights: ~10MB

---

## Docker Deployment

### docker-compose.yml (excerpt)

```yaml
services:
  ruvector:
    image: ghcr.io/ruvnet/ruvector:latest
    ports:
      - "6333:6333"
    volumes:
      - ruvector_data:/data
    environment:
      - RUVECTOR_DATA_DIR=/data
      - RUVECTOR_PORT=6333
      - RUVECTOR_ENABLE_GNN=true
      - RUVECTOR_ENABLE_SONA=true
      - RUVECTOR_ENABLE_GRAPH=true
      - RUVECTOR_LOG_LEVEL=info
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 10s
      timeout: 5s
      retries: 3

volumes:
  ruvector_data:
```

This replaces the previous 3-service Milvus deployment block:

```yaml
# REMOVED (previously required for Milvus):
# - etcd (port 2379)
# - minio (port 9000)
# - milvus-standalone (port 19530)
```

### Environment Variables

Add to `.env`:

```env
# RuVector
RUVECTOR_URL=http://ruvector:6333
RUVECTOR_TIMEOUT=30
```

---

## REST API Reference

### Health Check
```
GET /health
Response: {"status": "ok", "version": "1.0.0", "uptime_seconds": 12345}
```

### Collections
```
POST   /collections                     -- Create collection
GET    /collections                     -- List collections
GET    /collections/{name}              -- Get collection info
DELETE /collections/{name}              -- Delete collection
```

### Points (Documents)
```
POST   /collections/{name}/points       -- Insert point(s)
GET    /collections/{name}/points/{id}  -- Get point by ID
DELETE /collections/{name}/points/{id}  -- Delete point
POST   /collections/{name}/points/batch -- Batch insert
```

### Search
```
POST   /collections/{name}/search       -- Hybrid search
POST   /collections/{name}/search/vector -- Vector-only search
POST   /collections/{name}/search/bm25   -- BM25-only search
```

### Graph
```
POST   /graph/query                     -- Execute Cypher query
POST   /graph/edges                     -- Insert edge(s)
DELETE /graph/edges/{id}                -- Delete edge
```

### Admin
```
GET    /metrics                         -- Prometheus metrics
POST   /admin/compact                   -- Trigger compaction
POST   /admin/snapshot                  -- Create snapshot
GET    /admin/sona/status               -- SONA optimization status
GET    /admin/gnn/status                -- GNN learning status
```

---

## Troubleshooting

### RuVector service not starting
```bash
# Check logs
docker-compose logs ruvector

# Verify port is available
lsof -i :6333

# Check data directory permissions
ls -la data/ruvector/
```

### High search latency
1. Check if SONA is enabled (`GET /admin/sona/status`)
2. Verify GNN has enough training samples (`GET /admin/gnn/status`)
3. Review collection size vs available memory
4. Consider increasing `ef_search` parameter for better recall

### Connection refused from Python backend
```python
# Verify RuVector is reachable
import httpx
async with httpx.AsyncClient() as client:
    resp = await client.get("http://localhost:6333/health")
    print(resp.json())
```

---

## Further Reading

- [RuVector Repository](https://github.com/ruvnet/ruvector) -- Source code and documentation
- [System Summary](../SYSTEM_SUMMARY.md) -- Complete Crawlset architecture
- [Architecture Comparison](../ARCHITECTURE_COMPARISON.md) -- Detailed component comparison
- [README](../README.md) -- Project overview and quick start
