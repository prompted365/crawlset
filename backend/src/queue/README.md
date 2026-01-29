# Queue Module - Distributed Task Processing

This module provides distributed task processing infrastructure using Celery and Redis.

## Features

- **Priority Queues**: Three priority levels (realtime, batch, background)
- **Retry Logic**: Automatic retry with exponential backoff
- **Progress Tracking**: Real-time task progress updates
- **Resource Management**: Memory limits and connection pooling
- **Health Checks**: Worker health monitoring and statistics

## Architecture

### Queues

1. **Realtime Queue** (`realtime`)
   - Priority: High (10)
   - Tasks: URL extraction, enrichments
   - Concurrency: 4 workers
   - Rate Limit: 100/minute

2. **Batch Queue** (`batch`)
   - Priority: Medium (5)
   - Tasks: Batch extraction, webset processing
   - Concurrency: 2 workers
   - Timeout: 1-2 hours

3. **Background Queue** (`background`)
   - Priority: Low (1)
   - Tasks: Monitoring, cleanup
   - Concurrency: 1 worker
   - Timeout: 30 minutes

### Tasks

- `extract_url_task`: Extract content from a single URL
- `batch_extract_task`: Process multiple URLs in batch
- `process_webset_task`: Process webset search/refresh
- `run_monitor_task`: Execute monitor and update items
- `enrich_item_task`: Run enrichments on items
- `cleanup_expired_results`: Periodic cleanup (scheduled)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Redis

Update `.env` with Redis connection:

```bash
REDIS_URL=redis://localhost:6379/0
```

### 3. Start Redis

```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or using local installation
redis-server
```

## Running Workers

### Start All Workers (Default)

```bash
# From backend directory
python -m src.queue.workers

# Or using celery CLI directly
celery -A src.queue.celery_app worker --loglevel=info
```

### Start Specialized Workers

```bash
# Realtime worker (high-priority extraction)
python -m src.queue.workers --worker-type realtime

# Batch worker (webset processing)
python -m src.queue.workers --worker-type batch

# Background worker (monitoring, cleanup)
python -m src.queue.workers --worker-type background
```

### Custom Configuration

```bash
# Custom concurrency and queues
python -m src.queue.workers \
  --queues realtime batch \
  --concurrency 8 \
  --loglevel DEBUG \
  --max-tasks-per-child 50
```

### Production Deployment

For production, use multiple workers:

```bash
# Terminal 1: Realtime workers (4 processes)
celery -A src.queue.celery_app worker \
  --queues=realtime \
  --concurrency=4 \
  --max-tasks-per-child=100 \
  --loglevel=info \
  --logfile=/var/log/celery/realtime.log

# Terminal 2: Batch workers (2 processes)
celery -A src.queue.celery_app worker \
  --queues=batch \
  --concurrency=2 \
  --max-tasks-per-child=50 \
  --loglevel=info \
  --logfile=/var/log/celery/batch.log

# Terminal 3: Background worker (1 process)
celery -A src.queue.celery_app worker \
  --queues=background \
  --concurrency=1 \
  --max-tasks-per-child=100 \
  --loglevel=info \
  --logfile=/var/log/celery/background.log
```

## Task Usage

### From Python Code

```python
from src.queue.tasks import extract_url_task, batch_extract_task

# Async task execution
result = extract_url_task.delay("https://example.com")
print(f"Task ID: {result.id}")

# Get result (blocking)
data = result.get(timeout=30)
print(data)

# Check task status
print(f"Status: {result.status}")
print(f"Ready: {result.ready()}")

# Batch extraction
urls = ["https://example.com", "https://example.org"]
batch_result = batch_extract_task.delay(urls, webset_id="webset-123")
```

### Priority Execution

```python
# High priority (realtime queue)
result = extract_url_task.apply_async(
    args=["https://example.com"],
    priority=10,
    queue="realtime"
)

# Low priority (background queue)
result = extract_url_task.apply_async(
    args=["https://example.com"],
    priority=1,
    queue="background"
)
```

### Task Chaining

```python
from celery import chain

# Chain tasks together
workflow = chain(
    extract_url_task.s("https://example.com"),
    enrich_item_task.s("item-123")
)
result = workflow.apply_async()
```

## Monitoring

### Worker Health Check

```python
from src.queue.workers import get_worker_health

health = get_worker_health()
print(health)
# {
#   "status": "healthy",
#   "uptime_seconds": 3600,
#   "tasks": {
#     "total": 150,
#     "successes": 145,
#     "failures": 5
#   },
#   "resources": {
#     "memory_rss_mb": 256.5,
#     "cpu_percent": 15.2
#   }
# }
```

### Celery Flower (Web UI)

Install and run Flower for monitoring:

```bash
pip install flower
celery -A src.queue.celery_app flower --port=5555
```

Access at http://localhost:5555

### CLI Monitoring

```bash
# List active workers
celery -A src.queue.celery_app status

# List active tasks
celery -A src.queue.celery_app inspect active

# List scheduled tasks
celery -A src.queue.celery_app inspect scheduled

# Worker statistics
celery -A src.queue.celery_app inspect stats

# Registered tasks
celery -A src.queue.celery_app inspect registered
```

## Configuration

### Environment Variables

```bash
# Redis connection
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Worker settings
CELERY_WORKER_CONCURRENCY=4
CELERY_WORKER_MAX_TASKS_PER_CHILD=100
CELERY_WORKER_MAX_MEMORY_MB=512

# Database
SQLITE_DB=./data/websets.db
```

### Celery Beat (Periodic Tasks)

For periodic tasks like cleanup:

```bash
# Start beat scheduler
celery -A src.queue.celery_app beat --loglevel=info
```

## Error Handling

### Retry Configuration

Tasks automatically retry on failure:

- Max retries: 3 (configurable per task)
- Backoff: Exponential with jitter
- Max backoff: 10 minutes

### Dead Letter Queue

Failed tasks after max retries are tracked in the database:

```sql
SELECT * FROM extraction_jobs WHERE status='failed';
```

### Task Timeouts

- Soft limit: Warning before hard limit
- Hard limit: Task forcefully terminated
- Default: 55 minutes soft, 1 hour hard

## Performance Tuning

### Concurrency

Adjust based on workload:

```bash
# CPU-bound tasks: concurrency = CPU cores
celery -A src.queue.celery_app worker --concurrency=8

# I/O-bound tasks: concurrency = 2-3x CPU cores
celery -A src.queue.celery_app worker --concurrency=16
```

### Prefetch

Control task prefetch:

```bash
# Disable prefetch for long-running tasks
celery -A src.queue.celery_app worker --prefetch-multiplier=1

# Enable prefetch for short tasks
celery -A src.queue.celery_app worker --prefetch-multiplier=4
```

### Connection Pooling

Redis connection pool is configured in `celery_app.py`:

- Max retries: 10
- Retry on startup: True
- Connection timeout: 30s

## Troubleshooting

### Worker Won't Start

```bash
# Check Redis connection
redis-cli ping

# Check Celery config
python -c "from src.queue.celery_app import app; print(app.conf)"

# Verbose logging
celery -A src.queue.celery_app worker --loglevel=DEBUG
```

### Tasks Stuck

```bash
# Purge all queues
celery -A src.queue.celery_app purge

# Terminate task
celery -A src.queue.celery_app control revoke <task_id> --terminate
```

### Memory Issues

```bash
# Reduce max-tasks-per-child to restart workers more frequently
celery -A src.queue.celery_app worker --max-tasks-per-child=10

# Monitor memory
watch -n 1 'ps aux | grep celery | grep -v grep'
```

## Best Practices

1. **Use appropriate queues**: Realtime for urgent, batch for bulk, background for low-priority
2. **Set timeouts**: Always set reasonable task timeouts
3. **Monitor resources**: Track memory and CPU usage
4. **Log errors**: All task failures are logged and stored
5. **Test locally**: Test with single worker before scaling
6. **Scale horizontally**: Add more workers instead of increasing concurrency
7. **Use task chains**: Chain related tasks for complex workflows
8. **Handle failures**: Implement proper error handling and retries
9. **Clean up**: Regularly purge old results and logs
10. **Monitor health**: Use health checks and Flower for monitoring

## Related Documentation

- [Celery Documentation](https://docs.celeryproject.org/)
- [Redis Documentation](https://redis.io/documentation)
- [Preprocessing Module](../preprocessing/README.md)
