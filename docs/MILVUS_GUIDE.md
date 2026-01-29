# Milvus Integration Guide

Crawlset uses [Milvus](https://milvus.io) - an open-source vector database - for semantic search and knowledge storage. This guide covers everything you need to know.

## Why Milvus?

You get the benefits without the vendor lock-in that comes with hosted solutions:
- **Self-hosted** - Run it wherever you want
- **Production-ready** - Battle-tested at scale
- **Fast** - HNSW and IVF indexing for millisecond searches
- **Flexible** - Multiple distance metrics, hybrid search
- **Scalable** - Distributed deployment when you need it

## Quick Start

### Running Milvus

The easiest way is through Docker Compose (already included):

```bash
docker-compose up -d
```

This starts Milvus standalone on `localhost:19530`.

### First Operations

```python
from crawlset.milvus import create_client

# Connect
client = await create_client()

# Create collection
await client.create_collection(
    name="my_webset",
    dimension=384,  # sentence-transformers default
    metric="COSINE"
)

# Insert documents
await client.insert(
    collection="my_webset",
    documents=[
        {"id": "doc1", "text": "AI is transforming software development"},
        {"id": "doc2", "text": "Machine learning enables new possibilities"}
    ]
)

# Search
results = await client.search(
    collection="my_webset",
    query="artificial intelligence applications",
    top_k=10
)

for result in results:
    print(f"{result.score}: {result.text}")
```

## Architecture

```
┌───────────────┐
│  Application  │
└───────┬───────┘
        │
        ▼
┌───────────────┐     ┌──────────────┐
│ Milvus Client │────▶│   sentence-  │
│               │     │  transformers │
└───────┬───────┘     └──────────────┘
        │                     │
        │                     ▼
        │              ┌──────────────┐
        │              │    Redis     │
        │              │   (cache)    │
        │              └──────────────┘
        ▼
┌───────────────────────────────┐
│         Milvus Server         │
│  ┌─────────┐    ┌──────────┐ │
│  │ Vectors │    │ Metadata │ │
│  │ (HNSW)  │    │  (JSON)  │ │
│  └─────────┘    └──────────┘ │
└───────────────────────────────┘
```

##

 Implementation in Crawlset

### Location

All Milvus code is in `backend/src/milvus/`:

```
src/milvus/
├── __init__.py       # Public API
├── client.py         # MilvusClient class
├── embedder.py       # Embedding generation
├── search.py         # Hybrid search engine
└── collections.py    # Collection management
```

### Client (`client.py`)

The main interface to Milvus:

```python
class MilvusClient:
    """Async Milvus client for Crawlset."""

    async def create_collection(
        self,
        name: str,
        dimension: int = 384,
        metric: str = "COSINE"
    ) -> None:
        """Create a new collection."""

    async def insert(
        self,
        collection: str,
        documents: list[dict]
    ) -> list[str]:
        """Insert documents with auto-embedding."""

    async def search(
        self,
        collection: str,
        query: str,
        top_k: int = 10
    ) -> list[SearchResult]:
        """Semantic search."""

    async def hybrid_search(
        self,
        collection: str,
        query: str,
        alpha: float = 0.7,
        top_k: int = 10
    ) -> list[SearchResult]:
        """Hybrid semantic + keyword search."""

    async def get(
        self,
        collection: str,
        ids: list[str]
    ) -> list[dict]:
        """Get documents by ID."""

    async def delete(
        self,
        collection: str,
        ids: list[str]
    ) -> None:
        """Delete documents."""
```

### Embedder (`embedder.py`)

Handles embedding generation with caching:

```python
class EmbeddingGenerator:
    """Generate embeddings with sentence-transformers."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        redis_url: str = None
    ):
        self.model = SentenceTransformer(model_name)
        self.redis = redis.from_url(redis_url) if redis_url else None

    async def embed(self, text: str) -> list[float]:
        """Generate embedding with Redis caching."""
        # Check cache
        if self.redis:
            cached = await self.redis.get(f"embed:{hash(text)}")
            if cached:
                return json.loads(cached)

        # Generate
        embedding = self.model.encode(text).tolist()

        # Cache
        if self.redis:
            await self.redis.setex(
                f"embed:{hash(text)}",
                86400,  # 24 hours
                json.dumps(embedding)
            )

        return embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Batch embedding generation."""
        return self.model.encode(texts).tolist()
```

### Hybrid Search (`search.py`)

Combines vector similarity with keyword matching:

```python
class HybridSearchEngine:
    """Hybrid search combining Milvus + BM25."""

    def __init__(self, milvus_client: MilvusClient):
        self.milvus = milvus_client
        self.bm25 = BM25()

    async def search(
        self,
        collection: str,
        query: str,
        alpha: float = 0.7,  # 0.0 = pure keyword, 1.0 = pure semantic
        top_k: int = 10
    ) -> list[SearchResult]:
        """Hybrid search with configurable weighting."""
        # Vector search
        semantic_results = await self.milvus.search(
            collection, query, top_k=top_k*2
        )

        # Keyword search
        keyword_results = await self.bm25.search(
            collection, query, top_k=top_k*2
        )

        # Combine with RRF (Reciprocal Rank Fusion)
        combined = self._reciprocal_rank_fusion(
            semantic_results,
            keyword_results,
            alpha=alpha
        )

        return combined[:top_k]
```

## Embedding Models

Crawlset uses [sentence-transformers](https://www.sbert.net/) for embeddings.

### Default Model

**all-MiniLM-L6-v2**
- Dimensions: 384
- Speed: Very fast (~8000 sentences/sec)
- Quality: Good for most use cases
- Size: 80 MB

### Better Quality

**all-mpnet-base-v2**
- Dimensions: 768
- Speed: Moderate (~2500 sentences/sec)
- Quality: Better for complex queries
- Size: 420 MB

### Choosing a Model

```python
# In .env
EMBEDDING_MODEL=all-MiniLM-L6-v2  # Default
# EMBEDDING_MODEL=all-mpnet-base-v2  # Better quality

# Or in code
from crawlset.milvus import create_embedder

embedder = await create_embedder(model="all-mpnet-base-v2")
```

**Rule of thumb**: Start with the default. Switch to mpnet if you need better quality and can accept slower speed.

## Index Configuration

Milvus uses HNSW (Hierarchical Navigable Small World) indexing.

### Parameters

```python
await client.create_collection(
    name="my_collection",
    dimension=384,
    metric="COSINE",  # or "L2", "IP"
    index_params={
        "M": 16,              # Connections per layer (8-64)
        "efConstruction": 200  # Build-time search depth (100-500)
    }
)
```

**M (links per node)**:
- Lower (8-16): Less memory, faster writes, slower search
- Higher (32-64): More memory, slower writes, faster search
- Default: 16 (good balance)

**efConstruction (build quality)**:
- Lower (100-200): Faster indexing, lower recall
- Higher (300-500): Slower indexing, higher recall
- Default: 200 (good balance)

### Search Parameters

```python
results = await client.search(
    collection="my_collection",
    query="search query",
    top_k=10,
    search_params={"ef": 64}  # Search depth (10-500)
)
```

**ef (search depth)**:
- Lower (10-30): Faster but may miss results
- Higher (100-500): Slower but more thorough
- Default: 64 (good balance)
- Rule: ef ≥ top_k

## Performance Tuning

### 1. Batch Operations

Insert documents in batches, not one at a time:

```python
# Bad
for doc in documents:
    await client.insert(collection, [doc])

# Good
await client.insert(collection, documents)  # All at once
```

### 2. Redis Caching

Enable Redis caching for computed embeddings:

```python
embedder = await create_embedder(
    model="all-MiniLM-L6-v2",
    redis_url="redis://localhost:6379/0"
)
```

This speeds up repeated queries dramatically.

### 3. Connection Pooling

Reuse the client instance:

```python
# Bad
async def search_stuff():
    client = await create_client()
    results = await client.search(...)

# Good
client = await create_client()  # Create once

async def search_stuff():
    results = await client.search(...)  # Reuse
```

### 4. Parallel Searches

Search multiple collections in parallel:

```python
results = await asyncio.gather(
    client.search("collection1", query),
    client.search("collection2", query),
    client.search("collection3", query)
)
```

### 5. Limit Result Fields

Only fetch fields you need:

```python
results = await client.search(
    collection="my_collection",
    query="search query",
    output_fields=["id", "title", "url"]  # Not all fields
)
```

## Monitoring

### Milvus Web UI

Access the built-in web UI:

```bash
open http://localhost:9091
```

Shows:
- Collections and their stats
- Index status
- System resources
- Query performance

### Python

```python
# Collection stats
stats = await client.get_collection_stats("my_collection")
print(f"Documents: {stats['row_count']}")
print(f"Index: {stats['index_type']}")

# System stats
system = await client.get_system_stats()
print(f"Memory: {system['memory_used']} MB")
```

## Common Patterns

### Webset Integration

Each webset gets its own collection:

```python
from crawlset.websets import WebsetManager
from crawlset.milvus import create_client

manager = WebsetManager()
milvus = await create_client()

# Create webset + collection
webset = await manager.create(name="AI News")
await milvus.create_collection(f"webset_{webset.id}")

# Add items
for url in urls:
    content = await extract(url)
    await milvus.insert(
        f"webset_{webset.id}",
        [{"id": url, "text": content.text, "metadata": content.metadata}]
    )

# Search within webset
results = await milvus.search(
    f"webset_{webset.id}",
    query="latest AI breakthroughs"
)
```

### Enrichment Integration

Store enriched data in Milvus metadata:

```python
# Extract and enrich
content = await extract(url)
enrichments = await enrich(content)

# Store with enrichments
await milvus.insert(
    collection="my_webset",
    documents=[{
        "id": url,
        "text": content.text,
        "metadata": {
            **content.metadata,
            "enrichments": enrichments
        }
    }]
)

# Filter by enrichments
results = await milvus.search(
    collection="my_webset",
    query="tech companies",
    filter="enrichments['company']['industry'] == 'technology'"
)
```

### Multi-collection Search

Search across multiple websets:

```python
async def search_all_websets(query: str):
    websets = await manager.list_all()

    # Search all in parallel
    searches = [
        milvus.search(f"webset_{ws.id}", query)
        for ws in websets
    ]

    all_results = await asyncio.gather(*searches)

    # Combine and sort
    combined = []
    for results in all_results:
        combined.extend(results)

    combined.sort(key=lambda x: x.score, reverse=True)
    return combined[:20]
```

## Troubleshooting

### Connection Failed

```python
# Check if Milvus is running
docker-compose ps milvus-standalone

# Check logs
docker-compose logs milvus-standalone

# Restart
docker-compose restart milvus-standalone
```

### Slow Searches

- Lower `ef` parameter (trade recall for speed)
- Use batch operations
- Enable Redis caching
- Reduce `top_k`
- Use lighter embedding model

### Out of Memory

- Reduce `M` parameter (fewer connections)
- Use lighter embedding model (384 dims vs 768)
- Delete old collections
- Increase Docker memory limit

### Missing Results

- Increase `ef` parameter
- Check collection has data: `get_collection_stats()`
- Verify embeddings are generated
- Try pure vector search first (alpha=1.0)

## Production Deployment

### Distributed Milvus

For high scale, use distributed deployment:

```yaml
# docker-compose.prod.yml
services:
  milvus-etcd:
    image: quay.io/coreos/etcd:latest

  milvus-minio:
    image: minio/minio:latest

  milvus-rootcoord:
    image: milvusdb/milvus:latest
    command: milvus run rootcoord

  milvus-datacoord:
    image: milvusdb/milvus:latest
    command: milvus run datacoord

  milvus-querycoord:
    image: milvusdb/milvus:latest
    command: milvus run querycoord

  milvus-querynode:
    image: milvusdb/milvus:latest
    command: milvus run querynode
    deploy:
      replicas: 3

  milvus-datanode:
    image: milvusdb/milvus:latest
    command: milvus run datanode
    deploy:
      replicas: 2
```

### Backup

Regular backups:

```bash
# Backup collections
milvus-backup create --collection my_collection

# Restore
milvus-backup restore --collection my_collection
```

### Monitoring

Add Prometheus + Grafana:

```yaml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"
```

Milvus exports metrics on port 9091.

## Advanced Topics

### Custom Distance Metrics

```python
# Cosine similarity (default)
await client.create_collection(metric="COSINE")

# Euclidean distance
await client.create_collection(metric="L2")

# Inner product
await client.create_collection(metric="IP")
```

### Partition Management

Split large collections:

```python
# Create partitions (e.g., by date)
await client.create_partition("my_collection", "2025-01")

# Insert to specific partition
await client.insert(
    "my_collection",
    documents,
    partition="2025-01"
)

# Search specific partition
results = await client.search(
    "my_collection",
    query,
    partition="2025-01"
)
```

### Expression Filtering

Filter results:

```python
results = await client.search(
    "my_collection",
    query="AI research",
    filter="year >= 2023 and category == 'research'"
)
```

## Resources

- [Milvus Documentation](https://milvus.io/docs)
- [Sentence-Transformers](https://www.sbert.net/)
- [HNSW Paper](https://arxiv.org/abs/1603.09320)
- [Vector Databases Explained](https://www.pinecone.io/learn/vector-database/)

## Summary

Milvus gives you production-grade vector search without vendor lock-in. The integration in Crawlset handles the complexity - you just call simple async methods. Start with the defaults, tune as needed, scale when ready.
