# RuVector Integration Instructions

## Location
`/Users/breydentaylor/operationTorque/intelligence-pipeline/backend/src/ruvector/`

## Files to Create

### 1. `client.py`
- RuVectorClient class with async methods
- Connection to RuVector instance (file-based or server)
- Methods: insert_document, bulk_insert, hybrid_search, graph_query, delete_document
- Auto-embedding generation using sentence-transformers
- Graph operations support (nodes, edges, traversal)
- HNSW index configuration

### 2. `embedder.py`
- EmbeddingGenerator class using sentence-transformers
- Default model: 'all-MiniLM-L6-v2' (fast, 384 dims)
- Optional models: 'all-mpnet-base-v2' (quality, 768 dims)
- Batch embedding support
- Caching layer with Redis for computed embeddings
- Token counting and chunking

### 3. `search.py`
- HybridSearchEngine combining lexical + semantic
- Configurable alpha (semantic weight): 0.0-1.0
- BM25 for lexical search
- Vector similarity for semantic search
- Result fusion with RRF (Reciprocal Rank Fusion)
- Filtering by metadata
- Reranking integration

### 4. `graph.py`
- GraphOperations class for knowledge graph features
- Cypher-like query support (subset)
- Entity relationship extraction
- Path finding between documents
- Cluster analysis
- Community detection

### 5. `__init__.py`
- Export main classes

## Integration Points
- Database: Store RuVector doc IDs in webset_items.astradb_doc_id
- Extractors: Embed extracted content chunks
- Search: Use for webset search queries
- Enrichments: Graph queries for entity relationships

## Configuration (in config.py)
```python
RUVECTOR_DATA_DIR: str = "./data/ruvector"
RUVECTOR_ENABLE_GNN: bool = True
RUVECTOR_ENABLE_GRAPH: bool = True
EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
EMBEDDING_BATCH_SIZE: int = 32
```
