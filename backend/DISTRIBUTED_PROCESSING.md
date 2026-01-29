# Distributed Processing Layer

This document describes the distributed processing architecture for the intelligence pipeline.

## Overview

The distributed processing layer enables scalable, asynchronous processing of content extraction, enrichment, and monitoring tasks using Celery and Redis.

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│   FastAPI API   │────▶│ Redis Queue  │────▶│ Celery Workers  │
└─────────────────┘     └──────────────┘     └─────────────────┘
                              │                      │
                              │                      ▼
                              │              ┌─────────────────┐
                              │              │  Preprocessing  │
                              │              │  - Chunking     │
                              │              │  - Cleaning     │
                              │              │  - Reranking    │
                              │              └─────────────────┘
                              │                      │
                              ▼                      ▼
                        ┌──────────────────────────────┐
                        │      SQLite Database         │
                        │  + RuVector (Vector Store)   │
                        └──────────────────────────────┘
```

## Components

### 1. Queue Infrastructure (`src/queue/`)

- **celery_app.py**: Celery application with priority queues
- **tasks.py**: All task definitions with retry logic
- **workers.py**: Worker management and health checks

### 2. Preprocessing (`src/preprocessing/`)

- **chunker.py**: Semantic text chunking
- **cleaner.py**: Content cleaning and normalization
- **reranker.py**: Result reranking strategies

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Start Redis

```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or local
redis-server
```

### 3. Start Workers

```bash
# Terminal 1: Start all workers
python -m src.queue.workers

# Or specialized workers:
# Terminal 1: Realtime worker
python -m src.queue.workers --worker-type realtime

# Terminal 2: Batch worker
python -m src.queue.workers --worker-type batch

# Terminal 3: Background worker
python -m src.queue.workers --worker-type background
```

### 4. Start API Server

```bash
# Terminal 4: FastAPI server
uvicorn src.api.main:app --reload --port 8080
```

## Task Execution Flow

### URL Extraction Flow

```python
# 1. API receives request
POST /api/extract
{
  "url": "https://example.com",
  "use_playwright": false
}

# 2. Create extraction job
job_id = str(uuid.uuid4())
INSERT INTO extraction_jobs (id, url, status, created_at)

# 3. Queue task (realtime priority)
result = extract_url_task.delay(url, job_id)

# 4. Worker processes task
# - Fetch page (browser.py)
# - Parse HTML (parser/trafilatura_parser.py)
# - Clean content (preprocessing/cleaner.py)
# - Store result

# 5. Update job status
UPDATE extraction_jobs SET status='completed', result=..., completed_at=...

# 6. Return result
GET /api/extract/{job_id}
```

### Webset Processing Flow

```python
# 1. API receives webset refresh request
POST /api/websets/{webset_id}/refresh

# 2. Queue webset processing task
result = process_webset_task.delay(webset_id, action="refresh")

# 3. Worker loads webset items
SELECT url, content_hash FROM webset_items WHERE webset_id=?

# 4. For each item:
# - Extract content (extract_url_task)
# - Clean and chunk (preprocessing)
# - Compare hashes (detect changes)
# - Update database

# 5. Store updated items
UPDATE webset_items SET content=?, content_hash=?, last_crawled_at=?

# 6. Update webset timestamp
UPDATE websets SET updated_at=?
```

### Monitor Execution Flow

```python
# 1. Scheduler triggers monitor (APScheduler)
_run_monitor(db_path, monitor_id)

# 2. Or manual trigger
POST /api/monitors/{monitor_id}/run

# 3. Queue monitor task
result = run_monitor_task.delay(monitor_id)

# 4. Worker processes:
# - Load monitor config
# - Create monitor run record
# - Process webset (process_webset_task)
# - Update run status

# 5. Store results
INSERT INTO monitor_runs (id, monitor_id, status, items_updated, ...)
UPDATE monitors SET last_run_at=?
```

## Usage Examples

### Example 1: Single URL Extraction

```python
from src.queue.tasks import extract_url_task

# Submit task
result = extract_url_task.delay("https://example.com")

# Get task ID
print(f"Task ID: {result.id}")

# Wait for result (blocking)
data = result.get(timeout=60)
print(f"Title: {data['title']}")
print(f"Text length: {len(data['text'])}")
print(f"Links: {len(data['links'])}")
```

### Example 2: Batch Processing

```python
from src.queue.tasks import batch_extract_task

urls = [
    "https://example.com/page1",
    "https://example.com/page2",
    "https://example.com/page3",
]

# Submit batch task
result = batch_extract_task.delay(urls, webset_id="my-webset")

# Poll for progress
while not result.ready():
    if result.state == 'PROGRESS':
        meta = result.info
        print(f"Progress: {meta['completed']}/{meta['total']}")
    time.sleep(1)

# Get final result
summary = result.get()
print(f"Successful: {summary['successful']}")
print(f"Failed: {summary['failed']}")
```

### Example 3: Content Processing Pipeline

```python
from src.queue.tasks import extract_url_task
from src.preprocessing import clean_for_embedding, chunk_for_embedding

# Extract content
result = extract_url_task.apply(args=["https://example.com"]).get()
raw_text = result['text']

# Clean for embeddings
cleaned_text = clean_for_embedding(raw_text)

# Chunk into embedding-sized pieces
chunks = chunk_for_embedding(
    cleaned_text,
    max_tokens=512,
    overlap_tokens=50
)

# Process chunks (generate embeddings, store in RuVector)
for chunk in chunks:
    embedding = generate_embedding(chunk.text)
    store_in_vector_db(chunk.text, embedding, metadata={
        'url': result['url'],
        'chunk_index': chunk.index
    })
```

### Example 4: Search with Reranking

```python
from src.preprocessing import SearchResult, rerank_by_recency

# Search vector database
raw_results = search_vector_db(query="machine learning")

# Convert to SearchResult objects
results = [
    SearchResult(
        id=r['id'],
        text=r['text'],
        score=r['score'],
        metadata=r['metadata'],
        embedding=r['embedding']
    )
    for r in raw_results
]

# Rerank by recency and relevance
reranked = rerank_by_recency(
    results,
    recency_weight=0.4,
    score_weight=0.6,
    recency_decay_days=30
)

# Return top 10
return reranked[:10]
```

### Example 5: Monitor with Enrichment

```python
from src.queue.tasks import run_monitor_task, enrich_item_task

# Run monitor (updates webset items)
monitor_result = run_monitor_task.delay("monitor-123")

# Wait for completion
summary = monitor_result.get()
print(f"Items updated: {summary['result']['items_updated']}")

# Enrich updated items
from celery import group

# Get updated item IDs
updated_item_ids = get_updated_items("webset-123")

# Create parallel enrichment tasks
job = group(
    enrich_item_task.s(item_id, enrichment_types=['summary', 'entities'])
    for item_id in updated_item_ids
)

# Execute in parallel
result = job.apply_async()

# Wait for all to complete
result.get()
```

## Integration with API

### Add Task Endpoints to FastAPI

```python
# src/api/routes/tasks.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.queue.tasks import extract_url_task, batch_extract_task

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

class ExtractRequest(BaseModel):
    url: str
    use_playwright: bool = False

@router.post("/extract")
async def create_extract_task(req: ExtractRequest):
    """Submit URL extraction task."""
    result = extract_url_task.delay(req.url, use_playwright=req.use_playwright)
    return {
        "task_id": result.id,
        "status": result.status,
        "url": req.url
    }

@router.get("/extract/{task_id}")
async def get_extract_task(task_id: str):
    """Get extraction task status and result."""
    result = extract_url_task.AsyncResult(task_id)

    if result.ready():
        if result.successful():
            return {
                "task_id": task_id,
                "status": "completed",
                "result": result.result
            }
        else:
            return {
                "task_id": task_id,
                "status": "failed",
                "error": str(result.result)
            }
    else:
        return {
            "task_id": task_id,
            "status": result.state,
            "info": result.info
        }

class BatchExtractRequest(BaseModel):
    urls: list[str]
    webset_id: str = None

@router.post("/extract/batch")
async def create_batch_extract_task(req: BatchExtractRequest):
    """Submit batch extraction task."""
    result = batch_extract_task.delay(req.urls, req.webset_id)
    return {
        "task_id": result.id,
        "status": result.status,
        "total_urls": len(req.urls)
    }
```

## Monitoring and Debugging

### Check Task Status

```bash
# List active workers
celery -A src.queue.celery_app status

# List active tasks
celery -A src.queue.celery_app inspect active

# Check worker stats
celery -A src.queue.celery_app inspect stats
```

### Monitor with Flower

```bash
# Install
pip install flower

# Start Flower
celery -A src.queue.celery_app flower --port=5555

# Access at http://localhost:5555
```

### Check Worker Health

```python
from src.queue.workers import get_worker_health

health = get_worker_health()
print(f"Status: {health['status']}")
print(f"Uptime: {health['uptime_seconds']}s")
print(f"Memory: {health['resources']['memory_rss_mb']}MB")
print(f"Tasks: {health['tasks']['total']} total, {health['tasks']['failures']} failed")
```

### Debug Failed Tasks

```bash
# Check Redis for failed tasks
redis-cli
> LRANGE celery:failed 0 -1

# Check database for failed extraction jobs
sqlite3 data/websets.db
SELECT * FROM extraction_jobs WHERE status='failed' ORDER BY created_at DESC LIMIT 10;
```

## Performance Tuning

### Worker Configuration

```bash
# High-throughput realtime processing (short tasks)
celery -A src.queue.celery_app worker \
  --queues=realtime \
  --concurrency=8 \
  --prefetch-multiplier=4 \
  --max-tasks-per-child=100

# Batch processing (long tasks)
celery -A src.queue.celery_app worker \
  --queues=batch \
  --concurrency=2 \
  --prefetch-multiplier=1 \
  --max-tasks-per-child=10
```

### Redis Configuration

```bash
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
appendonly yes
```

### Rate Limiting

Tasks have built-in rate limits:

- `extract_url_task`: 100/minute
- `enrich_item_task`: 50/minute

Adjust in `celery_app.py` task_annotations.

## Error Handling

### Automatic Retries

All tasks automatically retry on failure:

```python
@app.task(
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3},
    retry_backoff=True,  # Exponential backoff
    retry_jitter=True,   # Add jitter
)
```

### Manual Retry

```python
from src.queue.tasks import extract_url_task

# Retry failed task
result = extract_url_task.AsyncResult("task-id")
if result.failed():
    result.retry()
```

### Dead Letter Queue

Failed tasks after max retries are logged:

```sql
SELECT * FROM extraction_jobs WHERE status='failed';
```

## Best Practices

1. **Queue Selection**
   - Use `realtime` for user-facing operations (<5 min)
   - Use `batch` for background processing (5-60 min)
   - Use `background` for maintenance (periodic tasks)

2. **Task Design**
   - Keep tasks idempotent (safe to retry)
   - Pass minimal data (IDs, not full objects)
   - Set appropriate timeouts
   - Log progress for long tasks

3. **Error Handling**
   - Always handle expected exceptions
   - Log errors with context
   - Update database status on failure
   - Use retry with exponential backoff

4. **Resource Management**
   - Set memory limits per worker
   - Use max-tasks-per-child to prevent leaks
   - Monitor worker health
   - Scale horizontally, not vertically

5. **Monitoring**
   - Use Flower for real-time monitoring
   - Track task success/failure rates
   - Monitor queue depths
   - Set up alerts for failures

## Deployment

### Docker Compose

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

  api:
    build: .
    command: uvicorn src.api.main:app --host 0.0.0.0 --port 8080
    ports:
      - "8080:8080"
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379/0

  worker-realtime:
    build: .
    command: celery -A src.queue.celery_app worker --queues=realtime --concurrency=4
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379/0

  worker-batch:
    build: .
    command: celery -A src.queue.celery_app worker --queues=batch --concurrency=2
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379/0

  worker-background:
    build: .
    command: celery -A src.queue.celery_app worker --queues=background --concurrency=1
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379/0

  flower:
    build: .
    command: celery -A src.queue.celery_app flower --port=5555
    ports:
      - "5555:5555"
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379/0

volumes:
  redis-data:
```

### Systemd Service

```ini
# /etc/systemd/system/celery-realtime.service
[Unit]
Description=Celery Realtime Worker
After=network.target redis.service

[Service]
Type=forking
User=celery
Group=celery
WorkingDirectory=/app/backend
ExecStart=/usr/local/bin/celery -A src.queue.celery_app worker \
  --queues=realtime \
  --concurrency=4 \
  --logfile=/var/log/celery/realtime.log \
  --pidfile=/var/run/celery/realtime.pid
ExecStop=/usr/local/bin/celery -A src.queue.celery_app control shutdown
Restart=always

[Install]
WantedBy=multi-user.target
```

## Next Steps

1. Implement LLM-based enrichments in `enrich_item_task`
2. Add cross-encoder model for semantic reranking
3. Implement semantic chunking with embeddings
4. Add task progress tracking in database
5. Create admin UI for task monitoring
6. Add metrics collection (Prometheus)
7. Implement task priority adjustment
8. Add webhook notifications for task completion

## Related Documentation

- [Queue Module README](src/queue/README.md)
- [Preprocessing Module README](src/preprocessing/README.md)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Redis Documentation](https://redis.io/documentation)
