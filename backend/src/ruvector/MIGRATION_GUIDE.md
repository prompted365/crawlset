# RuVector Migration Guide

Guide for integrating RuVector into the existing intelligence pipeline.

## Prerequisites

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure Redis is running (optional, for caching):
```bash
redis-server
```

## Step 1: Update Database Schema

The `webset_items.astradb_doc_id` field is already in the schema and can be used to store RuVector document IDs.

No migration needed - the field exists:
```python
class WebsetItem(Base):
    ...
    astradb_doc_id: Optional[str] = Column(String, nullable=True)
```

## Step 2: Initialize RuVector Client

Add to your application startup (e.g., `main.py` or as a FastAPI dependency):

```python
from ruvector import create_client
from config import get_settings

# Global client instance
ruvector_client = None

async def startup_event():
    """Initialize RuVector on startup."""
    global ruvector_client
    settings = get_settings()

    ruvector_client = await create_client(
        data_dir=settings.ruvector_data_dir,
        embedding_model=settings.embedding_model,
        redis_url=settings.redis_url,
    )
    logger.info("RuVector client initialized")

async def shutdown_event():
    """Cleanup RuVector on shutdown."""
    global ruvector_client
    if ruvector_client:
        await ruvector_client.close()
        logger.info("RuVector client closed")
```

Add to FastAPI app:
```python
app.add_event_handler("startup", startup_event)
app.add_event_handler("shutdown", shutdown_event)
```

## Step 3: Update Webset Item Creation

Modify your webset item creation to insert into RuVector:

### Before:
```python
async def create_webset_item(webset_id: str, url: str, content: str):
    item = WebsetItem(
        id=generate_id(),
        webset_id=webset_id,
        url=url,
        # ... other fields
    )
    session.add(item)
    await session.commit()
    return item
```

### After:
```python
async def create_webset_item(webset_id: str, url: str, content: str, title: str = None):
    global ruvector_client

    # Create database item
    item = WebsetItem(
        id=generate_id(),
        webset_id=webset_id,
        url=url,
        # ... other fields
    )

    # Insert into RuVector
    if content and ruvector_client:
        try:
            doc_id = await ruvector_client.insert_document(
                doc_id=item.id,
                text=content,
                metadata={
                    "webset_id": webset_id,
                    "url": url,
                    "title": title,
                    "created_at": item.created_at.isoformat(),
                }
            )
            item.astradb_doc_id = doc_id
            logger.info(f"Inserted document {doc_id} into RuVector")
        except Exception as e:
            logger.error(f"Failed to insert into RuVector: {e}")
            # Continue without vector storage

    session.add(item)
    await session.commit()
    return item
```

## Step 4: Update Extraction Pipeline

Integrate RuVector into the extraction pipeline to chunk and embed content:

```python
# In extractors/content.py or similar
from ruvector import get_client

async def extract_and_index(url: str, webset_id: str):
    # Extract content
    content = await extract_content(url)

    # Get RuVector client
    client = get_client()  # or use global instance

    # Chunk long documents
    if len(content["text"]) > 1000:
        chunks = client._embedder.chunk_text(
            content["text"],
            max_tokens=256,
            overlap=50
        )

        # Insert chunks
        for i, chunk in enumerate(chunks):
            await client.insert_document(
                doc_id=f"{webset_id}_{url_hash}_{i}",
                text=chunk,
                metadata={
                    "webset_id": webset_id,
                    "url": url,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "title": content.get("title"),
                }
            )
    else:
        # Insert whole document
        await client.insert_document(
            doc_id=f"{webset_id}_{url_hash}",
            text=content["text"],
            metadata={
                "webset_id": webset_id,
                "url": url,
                "title": content.get("title"),
            }
        )
```

## Step 5: Add Search Endpoints

Create new API endpoints for RuVector search:

```python
# In api/routes.py or api/search.py
from fastapi import APIRouter, Query
from ruvector import create_search_engine

router = APIRouter(prefix="/search", tags=["search"])

@router.get("/hybrid")
async def hybrid_search(
    query: str,
    webset_id: str = Query(None),
    top_k: int = Query(10, ge=1, le=100),
    alpha: float = Query(0.5, ge=0.0, le=1.0),
):
    """
    Hybrid search across webset documents.

    - query: Search query text
    - webset_id: Filter by webset ID (optional)
    - top_k: Number of results
    - alpha: Semantic weight (0=lexical, 1=semantic)
    """
    global ruvector_client

    # Create search engine
    search_engine = await create_search_engine(ruvector_client, alpha=alpha)

    # Filter by webset if specified
    filter_metadata = {"webset_id": webset_id} if webset_id else None

    # Search
    results = await search_engine.search(
        query=query,
        top_k=top_k,
        filter_metadata=filter_metadata,
    )

    return {
        "query": query,
        "alpha": alpha,
        "results": results,
    }

@router.get("/similar/{doc_id}")
async def find_similar(
    doc_id: str,
    top_k: int = Query(10, ge=1, le=100),
):
    """Find documents similar to a given document."""
    global ruvector_client

    search_engine = await create_search_engine(ruvector_client)
    results = await search_engine.get_similar_documents(doc_id, top_k=top_k)

    return {
        "source_doc_id": doc_id,
        "similar_documents": results,
    }
```

## Step 6: Add Graph Endpoints (Optional)

Add graph analysis endpoints:

```python
# In api/graph.py
from ruvector.graph import create_graph

@router.get("/graph/clusters")
async def find_clusters(
    eps: float = Query(0.3, ge=0.0, le=1.0),
    min_samples: int = Query(2, ge=1),
):
    """Find document clusters using DBSCAN."""
    global ruvector_client

    graph = await create_graph(ruvector_client)
    clusters = await graph.find_clusters(eps=eps, min_samples=min_samples)

    return {
        "num_clusters": len(clusters),
        "clusters": [
            {"cluster_id": i, "doc_ids": cluster, "size": len(cluster)}
            for i, cluster in enumerate(clusters)
        ]
    }

@router.get("/graph/path/{source_id}/{target_id}")
async def find_path(source_id: str, target_id: str, max_depth: int = Query(5)):
    """Find shortest path between two documents."""
    global ruvector_client

    graph = await create_graph(ruvector_client)
    await graph.build_graph_from_documents(similarity_threshold=0.5)

    path = await graph.find_path(source_id, target_id, max_depth=max_depth)

    if path:
        return {"path": path, "length": len(path) - 1}
    else:
        return {"path": None, "message": "No path found"}

@router.get("/graph/export")
async def export_graph(format: str = Query("json", regex="^(json|cytoscape)$")):
    """Export knowledge graph."""
    global ruvector_client

    graph = await create_graph(ruvector_client)
    await graph.build_graph_from_documents(similarity_threshold=0.5)

    graph_data = await graph.export_graph(format=format)
    return graph_data
```

## Step 7: Background Tasks for Indexing

Use Celery tasks for async indexing:

```python
# In queue/tasks.py
from celery import shared_task
from ruvector import create_client

@shared_task
def index_webset_item(item_id: str):
    """Background task to index a webset item in RuVector."""
    import asyncio

    async def _index():
        # Get item from database
        async with get_db_session() as session:
            item = await session.get(WebsetItem, item_id)
            if not item:
                return

            # Create client
            settings = get_settings()
            client = await create_client(
                data_dir=settings.ruvector_data_dir,
                embedding_model=settings.embedding_model,
            )

            try:
                # Index document
                doc_id = await client.insert_document(
                    doc_id=item.id,
                    text=item.content,  # Assuming content field exists
                    metadata={
                        "webset_id": item.webset_id,
                        "url": item.url,
                        "title": item.title,
                    }
                )

                # Update database
                item.astradb_doc_id = doc_id
                await session.commit()

            finally:
                await client.close()

    asyncio.run(_index())
```

## Step 8: Testing

Run the integration test:

```bash
cd backend/src/ruvector
python test_integration.py
```

Run example usage:

```bash
python example_usage.py
```

## Step 9: Monitoring and Maintenance

Add periodic tasks for maintenance:

```python
@shared_task
def rebuild_search_index():
    """Rebuild BM25 search index."""
    async def _rebuild():
        client = await create_client(...)
        search_engine = await create_search_engine(client)
        await search_engine.index_documents()
        await client.close()

    asyncio.run(_rebuild())

@shared_task
def update_graph():
    """Update knowledge graph."""
    async def _update():
        client = await create_client(...)
        graph = await create_graph(client)
        await graph.build_graph_from_documents(similarity_threshold=0.6)
        stats = await graph.get_graph_stats()
        logger.info(f"Graph updated: {stats}")
        await client.close()

    asyncio.run(_update())
```

## Rollback Plan

If issues arise:

1. **Disable RuVector**: Set `ruvector_client = None` to bypass vector operations
2. **Remove from pipeline**: Comment out RuVector calls in extraction/search
3. **Clear data**: Delete `./data/ruvector` directory to start fresh
4. **Database cleanup**: Set `astradb_doc_id = NULL` if needed

## Performance Tuning

1. **Embedding batch size**: Adjust based on memory
   ```python
   EMBEDDING_BATCH_SIZE=64  # Increase for more RAM
   ```

2. **HNSW parameters**: Tune for your use case
   ```python
   index_params = {
       "ef_construction": 200,  # Build quality
       "M": 16,                 # Connectivity
       "ef": 50,                # Search quality
   }
   ```

3. **Redis caching**: Essential for production
   ```python
   REDIS_URL=redis://localhost:6379/0
   ```

4. **Alpha tuning**: Adjust per query type
   - Keyword queries: `alpha=0.3`
   - Semantic queries: `alpha=0.7`
   - Balanced: `alpha=0.5`

## Next Steps

1. Run integration tests
2. Start with a small dataset (100-1000 documents)
3. Monitor performance metrics
4. Tune parameters based on results
5. Scale to full dataset
6. Enable graph features if needed

## Support

For issues or questions:
1. Check README.md for API reference
2. Review example_usage.py for patterns
3. Run test_integration.py to verify setup
4. Check logs for error messages
