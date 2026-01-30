# RuVector Integration

Production-ready vector database integration powered by the **RuVector Rust service**. Provides semantic search, hybrid search, knowledge graph, SONA self-learning, and GNN capabilities via async HTTP.

## Overview

The RuVector integration communicates with a dedicated Rust/Axum HTTP service that handles:

- **HNSW Vector Indexing**: Sub-millisecond approximate nearest neighbor search
- **Hybrid Search**: Combined lexical (BM25) and semantic (vector) search with RRF fusion
- **Graph Operations**: Cypher-like graph queries, path finding, clustering
- **SONA Self-Learning**: Self-Organizing Neural Architecture for adaptive optimization
- **GNN Training**: Graph Neural Network layers that improve recall over time
- **61us p50 Latency**: Rust/Axum delivers consistent ultra-low latency

## Architecture

```
Python Backend (FastAPI)          RuVector Service (Rust/Axum)
┌─────────────────────┐   HTTP   ┌──────────────────────────┐
│  ruvector/           │ ──────→ │  :6333                   │
│  ├── client.py       │  httpx  │  ├── /documents (CRUD)   │
│  ├── embedder.py     │ ←────── │  ├── /search (HNSW)      │
│  ├── search.py       │         │  ├── /graph/* (Cypher)    │
│  └── graph.py        │         │  ├── /sona/trajectory     │
└─────────────────────┘         │  └── /gnn/train           │
                                 └──────────────────────────┘
```

## Quick Start

### Prerequisites

The RuVector Rust service must be running:
```bash
# Via Docker Compose (recommended)
docker-compose up -d ruvector

# Verify health
curl http://localhost:6333/health
```

### Basic Usage

```python
from src.ruvector.client import RuVectorClient

# Create client (connects to Rust service via HTTP)
client = RuVectorClient(ruvector_url="http://localhost:6333")
await client.initialize()

# Insert a document
await client.insert_document(
    doc_id="doc1",
    text="Your document text here",
    metadata={"source": "web", "category": "tech"}
)

# Bulk insert
documents = [
    {"id": "doc2", "text": "Document 2 text", "metadata": {"category": "news"}},
    {"id": "doc3", "text": "Document 3 text", "metadata": {"category": "tech"}},
]
await client.bulk_insert(documents)

# Search
results = await client.hybrid_search("query text", top_k=10)
for result in results:
    print(f"{result['id']}: {result['score']:.3f}")
    print(f"  {result['text'][:100]}...")

# Cleanup
await client.close()
```

### Hybrid Search Engine

```python
from src.ruvector.search import HybridSearchEngine
from src.ruvector.client import RuVectorClient

client = RuVectorClient()
await client.initialize()
search_engine = HybridSearchEngine(client, alpha=0.5)

# alpha controls semantic vs lexical weighting:
# - 0.0 = pure lexical (BM25)
# - 0.5 = balanced hybrid
# - 1.0 = pure semantic (vector)

results = await search_engine.search("query", top_k=10)

# Multi-query search
results = await search_engine.multi_query_search(
    queries=["AI", "machine learning", "neural networks"],
    top_k=10
)

# Find similar documents
results = await search_engine.get_similar_documents("doc1", top_k=5)
```

### Graph Operations

```python
from src.ruvector.client import RuVectorClient

client = RuVectorClient()
await client.initialize()

# Build graph from documents (creates similarity edges in Rust service)
await client.build_graph(similarity_threshold=0.7)

# Find path between documents
path = await client.find_path("doc1", "doc10", max_depth=5)
print(f"Path: {' -> '.join(path)}")

# Find clusters
clusters = await client.find_clusters()
for i, cluster in enumerate(clusters):
    print(f"Cluster {i}: {len(cluster)} documents")

# Get neighbors
neighbors = await client.get_neighbors("doc1")

# Execute Cypher-like graph query
result = await client.graph_query("MATCH (n)-[:SIMILAR]->(m) RETURN n, m")
```

### SONA Self-Learning

```python
# After successful extraction, send trajectory data
await client.send_sona_trajectory(
    actions=[
        {"type": "fetch", "url": "https://example.com", "success": True},
        {"type": "parse", "parser": "trafilatura", "success": True},
        {"type": "enrich", "plugin": "content_enricher", "success": True},
    ],
    reward=0.92,
)
```

### GNN Training

```python
# Send query-result interaction data for self-learning
await client.train_gnn(
    interactions=[
        {"query": "AI healthcare", "doc_id": "doc1", "relevance": 0.95},
        {"query": "machine learning", "doc_id": "doc2", "relevance": 0.87},
    ],
)
```

## Configuration

Environment variables:

```bash
# RuVector Rust service URL
RUVECTOR_URL=http://localhost:6333

# Feature flags
RUVECTOR_ENABLE_GNN=true
RUVECTOR_ENABLE_GRAPH=true

# Embedding Configuration (Python-side)
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_BATCH_SIZE=32

# Redis for embedding caching (optional)
REDIS_URL=redis://localhost:6379/0
```

## API Reference

### RuVectorClient

```python
class RuVectorClient:
    def __init__(ruvector_url: str = "http://localhost:6333")

    async def initialize() -> None
    async def health_check() -> Dict
    async def insert_document(doc_id: str, text: str, metadata: Dict) -> str
    async def bulk_insert(documents: List[Dict], batch_size: int) -> List[str]
    async def hybrid_search(query: str, top_k: int) -> List[Dict]
    async def get_document(doc_id: str) -> Optional[Dict]
    async def delete_document(doc_id: str) -> bool
    async def graph_query(cypher: str) -> Any
    async def build_graph(similarity_threshold: float) -> Dict
    async def find_path(source: str, target: str, max_depth: int) -> List[str]
    async def find_clusters() -> List[List[str]]
    async def get_neighbors(node_id: str) -> List[Dict]
    async def send_sona_trajectory(actions: List, reward: float) -> Dict
    async def train_gnn(interactions: List) -> Dict
    async def get_stats() -> Dict
    async def close() -> None
```

### HybridSearchEngine

```python
class HybridSearchEngine:
    async def index_documents() -> None
    async def search(query: str, top_k: int) -> List[Dict]
    async def get_similar_documents(doc_id: str, top_k: int) -> List[Dict]
    async def multi_query_search(queries: List[str], top_k: int) -> List[Dict]
    def set_alpha(alpha: float) -> None
    def get_stats() -> Dict
```

### GraphOperations

```python
class GraphOperations:
    async def build_graph_from_documents(similarity_threshold: float) -> None
    async def find_path(source_id: str, target_id: str, max_depth: int) -> List[str]
    async def find_clusters(eps: float, min_samples: int) -> List[List[str]]
    async def get_neighbors(doc_id: str, max_depth: int) -> List[Dict]
    async def execute_query(cypher: str) -> Any
    async def get_graph_stats() -> Dict
    async def export_graph(format: str) -> Any
```

## Dependencies

Required packages:
- `httpx` - Async HTTP client (communicates with Rust service)
- `sentence-transformers>=3.3.1` - Embedding generation (Python-side)
- `numpy>=2.2.1` - Array operations
- `redis>=5.2.1` - Embedding caching (optional)

The Rust service handles HNSW indexing, graph operations, SONA, and GNN internally.

## Testing

Run the integration test (requires RuVector service running):

```bash
cd backend/src/ruvector
python test_integration.py
```

## Performance

| Operation | Latency | Notes |
|-----------|---------|-------|
| Insert | <1ms | Single document |
| Bulk Insert | ~10ms/100 docs | Batched |
| Search | 61us p50 | HNSW approximate |
| Graph Query | <5ms | Cypher traversal |
| Memory | 200MB/1M vectors | HNSW index |

## License

Part of the intelligence-pipeline project. RuVector designed by [Ruv](https://github.com/ruvnet).
