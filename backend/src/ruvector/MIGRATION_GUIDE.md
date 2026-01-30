# RuVector Migration Guide

Guide for migrating from the old in-process hnswlib/Milvus setup to the new RuVector Rust HTTP service.

## What Changed

| Before | After |
|--------|-------|
| 3-service Milvus stack (etcd + MinIO + standalone) | 1 RuVector Rust service |
| In-process hnswlib Python library | HTTP client (httpx) to Rust/Axum |
| `pymilvus` + `hnswlib` + `marshmallow` dependencies | `httpx` (already in requirements) |
| `data_dir` parameter for local index files | `ruvector_url` parameter for HTTP endpoint |
| `milvus_doc_id` field in database | `ruvector_doc_id` field in database |

## Prerequisites

1. RuVector Rust service running (via Docker Compose):
```bash
docker-compose up -d ruvector
curl http://localhost:6333/health
```

2. Updated Python dependencies:
```bash
pip install -r requirements.txt
```

## Step 1: Update Environment

Add to your `.env`:
```bash
RUVECTOR_URL=http://localhost:6333
```

Remove (no longer needed):
```bash
# MILVUS_HOST=localhost
# MILVUS_PORT=19530
```

## Step 2: Update Client Initialization

### Before:
```python
from ruvector import create_client

client = await create_client(
    data_dir="./data/ruvector",
    embedding_model="all-MiniLM-L6-v2",
    redis_url="redis://localhost:6379/0",
)
```

### After:
```python
from src.ruvector.client import RuVectorClient

client = RuVectorClient(ruvector_url="http://localhost:6333")
await client.initialize()
```

The client now communicates with the Rust service via HTTP. Embeddings are still generated Python-side and sent as float arrays.

## Step 3: Update Database References

The `milvus_doc_id` column has been renamed to `ruvector_doc_id`:

```python
# Before
webset_item.milvus_doc_id = doc_id

# After
webset_item.ruvector_doc_id = doc_id
```

## Step 4: Update Imports

```python
# Before (removed)
from pymilvus import connections, Collection
import hnswlib

# After
from src.ruvector.client import RuVectorClient
```

## Step 5: Use New Graph, SONA, and GNN Features

The Rust service provides additional capabilities:

```python
client = RuVectorClient()
await client.initialize()

# Graph operations (delegated to Rust)
await client.build_graph(similarity_threshold=0.7)
path = await client.find_path("doc1", "doc10")
clusters = await client.find_clusters()

# SONA self-learning
await client.send_sona_trajectory(
    actions=[{"type": "fetch", "success": True}],
    reward=0.9,
)

# GNN training
await client.train_gnn(
    interactions=[{"query": "AI", "doc_id": "doc1", "relevance": 0.95}],
)
```

## Step 6: Docker Compose Changes

The `docker-compose.yml` has been updated:
- **Removed**: `milvus-etcd`, `milvus-minio`, `milvus-standalone` (3 services)
- **Added**: `ruvector` (1 service on port 6333)

All backend and worker services now receive `RUVECTOR_URL=http://ruvector:6333`.

## Step 7: Celery Tasks

New Operation Torque Celery tasks are available:

```python
from src.queue.tasks import (
    send_sona_trajectory_task,
    train_gnn_task,
    boris_batch_vectorize_task,
)

# Send SONA trajectory after extraction
send_sona_trajectory_task.delay(
    actions=[...],
    reward=0.92,
)

# Train GNN with query interactions
train_gnn_task.delay(
    interactions=[...],
)

# Boris-style batch vectorization
boris_batch_vectorize_task.delay(
    webset_id="webset_123",
    batch_size=100,
)
```

## Rollback Plan

If issues arise:

1. **Disable RuVector**: Set `RUVECTOR_URL` to empty; client falls back gracefully
2. **Revert Docker**: Restore old `docker-compose.yml` with Milvus services
3. **Revert client**: The `RuVectorClient` constructor still accepts `data_dir` and `**kwargs` for backward compatibility
4. **Database**: The `ruvector_doc_id` column is backward compatible

## Verification

```bash
# 1. RuVector service healthy
curl http://localhost:6333/health

# 2. Backend reports RuVector connected
curl http://localhost:8000/health

# 3. Create a webset and extract a URL
curl -X POST http://localhost:8000/api/websets \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "search_query": "test"}'

# 4. Search returns results
curl -X POST http://localhost:8000/api/search/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 5}'
```
