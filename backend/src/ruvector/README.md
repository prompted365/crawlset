# RuVector Integration

Production-ready vector database integration for the intelligence pipeline, providing semantic search, hybrid search, and knowledge graph capabilities.

## Overview

The RuVector integration provides:

- **Vector Storage**: Efficient document storage with HNSW indexing
- **Auto-Embedding**: Automatic embedding generation using sentence-transformers
- **Hybrid Search**: Combined lexical (BM25) and semantic (vector) search with RRF fusion
- **Graph Operations**: Knowledge graph features with entity extraction and clustering
- **Caching**: Redis-based embedding cache for performance optimization
- **Async/Await**: Full async support for non-blocking operations

## Architecture

```
ruvector/
├── client.py       # RuVectorClient - Core vector database client
├── embedder.py     # EmbeddingGenerator - Text embedding with caching
├── search.py       # HybridSearchEngine - BM25 + vector search
├── graph.py        # GraphOperations - Knowledge graph features
└── __init__.py     # Public API exports
```

## Quick Start

### Basic Usage

```python
from ruvector import create_client

# Create and initialize client
client = await create_client(
    data_dir="./data/ruvector",
    embedding_model="all-MiniLM-L6-v2",
    redis_url="redis://localhost:6379/0"
)

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
from ruvector import create_client, create_search_engine

client = await create_client(data_dir="./data/ruvector")
search_engine = await create_search_engine(client, alpha=0.5)

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
from ruvector import create_client
from ruvector.graph import create_graph

client = await create_client(data_dir="./data/ruvector")
graph = await create_graph(client)

# Build graph from documents (creates similarity edges)
await graph.build_graph_from_documents(similarity_threshold=0.7)

# Find path between documents
path = await graph.find_path("doc1", "doc10", max_depth=5)
print(f"Path: {' -> '.join(path)}")

# Find clusters
clusters = await graph.find_clusters(eps=0.3, min_samples=2)
for i, cluster in enumerate(clusters):
    print(f"Cluster {i}: {len(cluster)} documents")

# Get neighbors
neighbors = await graph.get_neighbors("doc1", max_depth=2)

# Export graph
graph_data = await graph.export_graph(format="json")
# or format="cytoscape" for Cytoscape.js
```

## Configuration

Add to your `config.py` or `.env`:

```python
# RuVector Configuration
RUVECTOR_DATA_DIR: str = "./data/ruvector"
RUVECTOR_ENABLE_GNN: bool = True
RUVECTOR_ENABLE_GRAPH: bool = True

# Embedding Configuration
EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
EMBEDDING_BATCH_SIZE: int = 32

# Redis for caching (optional)
REDIS_URL: str = "redis://localhost:6379/0"
```

## Embedding Models

Available sentence-transformers models:

| Model | Dimensions | Max Tokens | Speed | Quality |
|-------|------------|------------|-------|---------|
| all-MiniLM-L6-v2 | 384 | 256 | Fast | Good |
| all-mpnet-base-v2 | 768 | 384 | Medium | Better |
| all-MiniLM-L12-v2 | 384 | 256 | Fast | Good |

Choose based on your performance/quality tradeoffs:
- **Fast**: `all-MiniLM-L6-v2` (recommended default)
- **Quality**: `all-mpnet-base-v2`

## API Reference

### RuVectorClient

```python
class RuVectorClient:
    async def initialize() -> None
    async def insert_document(doc_id: str, text: str, metadata: Dict) -> str
    async def bulk_insert(documents: List[Dict], batch_size: int) -> List[str]
    async def hybrid_search(query: str, top_k: int, filter_metadata: Dict) -> List[Dict]
    async def get_document(doc_id: str) -> Optional[Dict]
    async def delete_document(doc_id: str) -> bool
    async def graph_query(cypher: str) -> Any
    async def get_stats() -> Dict
    async def close() -> None
```

### EmbeddingGenerator

```python
class EmbeddingGenerator:
    async def initialize() -> None
    async def embed(text: str) -> np.ndarray
    async def embed_batch(texts: List[str], batch_size: int) -> List[np.ndarray]
    async def embed_documents(documents: List[Dict], text_field: str) -> List[Dict]
    def chunk_text(text: str, max_tokens: int, overlap: int) -> List[str]
    def count_tokens(text: str) -> int
    async def close() -> None
```

### HybridSearchEngine

```python
class HybridSearchEngine:
    async def index_documents() -> None
    async def search(query: str, top_k: int, filter_metadata: Dict, rerank: bool) -> List[Dict]
    async def get_similar_documents(doc_id: str, top_k: int) -> List[Dict]
    async def multi_query_search(queries: List[str], top_k: int) -> List[Dict]
    def set_alpha(alpha: float) -> None
    def get_stats() -> Dict
```

### GraphOperations

```python
class GraphOperations:
    async def build_graph_from_documents(similarity_threshold: float) -> None
    async def find_path(source_id: str, target_id: str, max_depth: int) -> Optional[List[str]]
    async def find_clusters(eps: float, min_samples: int) -> List[List[str]]
    async def get_neighbors(doc_id: str, edge_type: str, max_depth: int) -> List[Dict]
    async def extract_entities(text: str, entity_types: List[str]) -> List[Dict]
    async def execute_query(cypher: str) -> Any
    async def get_graph_stats() -> Dict
    async def export_graph(format: str) -> Any
```

## Integration Points

### Database Integration

Store RuVector document IDs in the SQLAlchemy database:

```python
from database.models import WebsetItem

# After inserting into RuVector
doc_id = await ruvector_client.insert_document(...)

# Store reference in database
webset_item.astradb_doc_id = doc_id
await session.commit()
```

### Extractor Integration

Embed extracted content chunks:

```python
from extractors import extract_content
from ruvector import create_client

client = await create_client(data_dir="./data/ruvector")

# Extract content
content = await extract_content(url)

# Chunk and embed
chunks = client._embedder.chunk_text(content["text"], max_tokens=256)
for i, chunk in enumerate(chunks):
    await client.insert_document(
        doc_id=f"{webset_id}_{i}",
        text=chunk,
        metadata={
            "url": url,
            "chunk_index": i,
            "total_chunks": len(chunks),
        }
    )
```

### Search Integration

Use for webset search queries:

```python
from ruvector import create_search_engine

# In your search endpoint
search_engine = await create_search_engine(client, alpha=0.7)
results = await search_engine.search(
    query=query_text,
    top_k=20,
    filter_metadata={"webset_id": webset_id}
)
```

## Performance Tips

1. **Batch Operations**: Use `bulk_insert()` instead of individual `insert_document()` calls
2. **Redis Caching**: Enable Redis to cache embeddings and avoid recomputation
3. **Batch Size**: Adjust `embedding_batch_size` based on available memory
4. **Index Parameters**: Tune HNSW parameters for your use case:
   - Increase `ef_construction` for better quality (slower build)
   - Increase `M` for better connectivity (more memory)
   - Increase `ef` for better search quality (slower search)
5. **Alpha Tuning**: Adjust search `alpha` based on query type:
   - Keyword queries: lower alpha (more lexical)
   - Semantic queries: higher alpha (more vector)

## Testing

Run the integration test:

```bash
cd backend/src/ruvector
python test_integration.py
```

## Dependencies

Required packages (added to `requirements.txt`):
- `sentence-transformers>=3.3.1` - Embedding generation
- `hnswlib>=0.8.0` - HNSW vector index
- `numpy>=2.2.1` - Array operations
- `scikit-learn>=1.5.2` - Clustering (DBSCAN)
- `redis>=5.2.1` - Caching (optional)

## Future Enhancements

- [ ] Cross-encoder reranking support
- [ ] Multi-vector representations
- [ ] Advanced entity extraction (spaCy, BERT-NER)
- [ ] Graph neural network features
- [ ] Real-time index updates without full rebuild
- [ ] Distributed index sharding
- [ ] Custom tokenizers for BM25
- [ ] Query expansion and refinement
- [ ] Relevance feedback

## License

Part of the intelligence-pipeline project.
