# Webset System Integration Guide

This guide shows how to integrate the webset management and monitoring system into your existing intelligence pipeline.

## Quick Start

### 1. Install Dependencies

Add to your `requirements.txt`:
```txt
sqlalchemy>=2.0.36
aiosqlite>=0.20.0
apscheduler>=3.10.4
```

Optional for enrichments:
```txt
openai>=1.59.7
anthropic>=0.42.0
instructor>=1.7.2
```

Install:
```bash
pip install -r requirements.txt
```

### 2. Initialize Database

```python
from src.websets import WebsetManager

async def init_system():
    manager = WebsetManager("sqlite+aiosqlite:///./data/websets.db")
    await manager.init_db()
    print("Database initialized!")

# Run initialization
import asyncio
asyncio.run(init_system())
```

### 3. Start the Scheduler

Add to your FastAPI app startup:

```python
# src/api/main.py
from fastapi import FastAPI
from src.monitors import start_scheduler

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    # Start monitor scheduler
    app.state.scheduler = await start_scheduler(
        db_url="sqlite:///./data/scheduler.db",
        manager_db_url="sqlite+aiosqlite:///./data/websets.db"
    )
    print("Monitor scheduler started")

@app.on_event("shutdown")
async def shutdown_event():
    # Shutdown scheduler gracefully
    app.state.scheduler.shutdown(wait=True)
    print("Monitor scheduler stopped")
```

## FastAPI Integration

### Update Existing Routes

Update `/Users/breydentaylor/operationTorque/intelligence-pipeline/backend/src/api/routes/websets.py`:

```python
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from ...websets import WebsetManager
from ...monitors import MonitorExecutor

router = APIRouter()

# Dependency to get manager
async def get_manager():
    manager = WebsetManager("sqlite+aiosqlite:///./data/websets.db")
    await manager.init_db()
    return manager

# Create webset
@router.post("/websets")
async def create_webset(
    name: str,
    search_query: Optional[str] = None,
    entity_type: Optional[str] = None,
    manager: WebsetManager = Depends(get_manager)
):
    webset = await manager.create_webset(
        name=name,
        search_query=search_query,
        entity_type=entity_type
    )
    return webset.to_dict()

# List websets
@router.get("/websets")
async def list_websets(
    limit: int = 100,
    offset: int = 0,
    manager: WebsetManager = Depends(get_manager)
):
    websets = await manager.list_websets(limit=limit, offset=offset)
    return [ws.to_dict() for ws in websets]

# Get webset
@router.get("/websets/{webset_id}")
async def get_webset(
    webset_id: str,
    manager: WebsetManager = Depends(get_manager)
):
    webset = await manager.get_webset(webset_id)
    if not webset:
        raise HTTPException(status_code=404, detail="Webset not found")
    return webset.to_dict()

# Add item to webset
@router.post("/websets/{webset_id}/items")
async def add_item(
    webset_id: str,
    url: str,
    title: Optional[str] = None,
    manager: WebsetManager = Depends(get_manager)
):
    item = await manager.add_item(
        webset_id=webset_id,
        url=url,
        title=title
    )
    if not item:
        raise HTTPException(status_code=404, detail="Webset not found")
    return item.to_dict()

# Create monitor
@router.post("/websets/{webset_id}/monitors")
async def create_monitor(
    webset_id: str,
    cron_expression: str,
    behavior_type: str,
    behavior_config: Optional[dict] = None,
    timezone: str = "UTC",
    manager: WebsetManager = Depends(get_manager)
):
    monitor = await manager.create_monitor(
        webset_id=webset_id,
        cron_expression=cron_expression,
        behavior_type=behavior_type,
        behavior_config=behavior_config,
        timezone=timezone
    )
    if not monitor:
        raise HTTPException(status_code=404, detail="Webset not found")

    # Add to scheduler
    from ...monitors import MonitorScheduler
    scheduler = MonitorScheduler()
    await scheduler.add_monitor_job(
        monitor_id=monitor.id,
        cron_expression=cron_expression,
        timezone=timezone
    )

    return monitor.to_dict()

# Run monitor immediately
@router.post("/monitors/{monitor_id}/run")
async def run_monitor(monitor_id: str):
    executor = MonitorExecutor()
    result = await executor.execute_monitor(monitor_id)
    return result.to_dict()

# Get monitor status
@router.get("/monitors/{monitor_id}")
async def get_monitor_status(monitor_id: str):
    executor = MonitorExecutor()
    status = await executor.get_monitor_status(monitor_id)
    return status
```

## Background Tasks Integration

### Using Celery (Optional)

If you're using Celery, you can create tasks for monitor execution:

```python
# src/tasks/webset_tasks.py
from celery import Celery
from src.monitors import MonitorExecutor
import asyncio

celery_app = Celery('tasks', broker='redis://localhost:6379')

@celery_app.task
def execute_monitor_task(monitor_id: str):
    """Execute a monitor as a Celery task."""
    executor = MonitorExecutor()

    # Run async function in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            executor.execute_monitor(monitor_id)
        )
        return result.to_dict()
    finally:
        loop.close()

@celery_app.task
def enrich_webset_items(webset_id: str, plugin_names: list = None):
    """Enrich all items in a webset."""
    from src.websets import WebsetManager
    from src.enrichments import CachedEnrichmentEngine

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        async def enrich():
            manager = WebsetManager()
            await manager.init_db()

            items = await manager.get_items(webset_id, limit=1000)

            engine = CachedEnrichmentEngine()
            # Auto-discover plugins
            engine.auto_discover_plugins("src.enrichments.plugins")

            for item in items:
                if item.content:
                    results = await engine.enrich(
                        content=item.content,
                        plugin_names=plugin_names
                    )

                    # Update item with enrichments
                    enrichments = {
                        name: result.to_dict()
                        for name, result in results.items()
                    }
                    await manager.update_item(
                        item_id=item.id,
                        enrichments=enrichments
                    )

            return len(items)

        return loop.run_until_complete(enrich())
    finally:
        loop.close()
```

## CLI Commands

Create a CLI for managing websets:

```python
# cli.py
import asyncio
import click
from src.websets import WebsetManager
from src.monitors import MonitorScheduler, MonitorExecutor

@click.group()
def cli():
    """Webset management CLI."""
    pass

@cli.command()
@click.argument('name')
@click.option('--query', help='Search query')
@click.option('--entity-type', help='Entity type')
def create_webset(name, query, entity_type):
    """Create a new webset."""
    async def _create():
        manager = WebsetManager()
        await manager.init_db()
        webset = await manager.create_webset(
            name=name,
            search_query=query,
            entity_type=entity_type
        )
        click.echo(f"Created webset: {webset.id}")
        click.echo(f"Name: {webset.name}")

    asyncio.run(_create())

@cli.command()
def list_websets():
    """List all websets."""
    async def _list():
        manager = WebsetManager()
        await manager.init_db()
        websets = await manager.list_websets()

        for ws in websets:
            click.echo(f"{ws.id}: {ws.name} ({ws.entity_type or 'no type'})")

    asyncio.run(_list())

@cli.command()
@click.argument('monitor_id')
def run_monitor(monitor_id):
    """Run a monitor immediately."""
    async def _run():
        executor = MonitorExecutor()
        click.echo(f"Running monitor {monitor_id}...")
        result = await executor.execute_monitor(monitor_id)
        click.echo(f"✓ Completed: {result.items_added} added, {result.items_updated} updated")
        if result.errors:
            click.echo(f"✗ Errors: {len(result.errors)}")

    asyncio.run(_run())

@cli.command()
def start_scheduler():
    """Start the monitor scheduler."""
    async def _start():
        from src.monitors import start_scheduler
        scheduler = await start_scheduler()
        click.echo("Scheduler started. Press Ctrl+C to stop.")

        try:
            # Keep running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            scheduler.shutdown()
            click.echo("\nScheduler stopped.")

    asyncio.run(_start())

if __name__ == '__main__':
    cli()
```

Usage:
```bash
# Create webset
python cli.py create-webset "AI Companies" --query "artificial intelligence" --entity-type company

# List websets
python cli.py list-websets

# Run monitor
python cli.py run-monitor mon-123

# Start scheduler
python cli.py start-scheduler
```

## Testing

Create tests for your integration:

```python
# tests/test_websets_integration.py
import pytest
from src.websets import WebsetManager
from src.monitors import MonitorExecutor

@pytest.mark.asyncio
async def test_create_and_search_webset():
    """Test creating a webset and searching for items."""
    manager = WebsetManager("sqlite+aiosqlite:///:memory:")
    await manager.init_db()

    # Create webset
    webset = await manager.create_webset(
        name="Test Webset",
        search_query="test query"
    )
    assert webset.name == "Test Webset"

    # Add item
    item = await manager.add_item(
        webset_id=webset.id,
        url="https://example.com",
        title="Test Page"
    )
    assert item.url == "https://example.com"

    # Get items
    items = await manager.get_items(webset.id)
    assert len(items) == 1

@pytest.mark.asyncio
async def test_monitor_execution():
    """Test monitor execution."""
    manager = WebsetManager("sqlite+aiosqlite:///:memory:")
    await manager.init_db()

    # Create webset
    webset = await manager.create_webset(name="Test")

    # Add item
    await manager.add_item(
        webset_id=webset.id,
        url="https://example.com",
        content="Test content"
    )

    # Create monitor
    monitor = await manager.create_monitor(
        webset_id=webset.id,
        cron_expression="0 * * * *",
        behavior_type="refresh"
    )

    # Execute monitor
    executor = MonitorExecutor(db_url="sqlite+aiosqlite:///:memory:")
    result = await executor.execute_monitor(monitor.id)

    assert result.items_updated >= 0
```

Run tests:
```bash
pytest tests/test_websets_integration.py -v
```

## Docker Integration

Add to your `docker-compose.yml`:

```yaml
services:
  backend:
    build: ./backend
    volumes:
      - ./backend/data:/app/data
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///./data/websets.db
      - RUVECTOR_DATA_DIR=/app/data/ruvector
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - scheduler

  scheduler:
    build: ./backend
    command: python -m src.monitors.scheduler
    volumes:
      - ./backend/data:/app/data
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///./data/websets.db
```

## Monitoring and Observability

### Prometheus Metrics

Add metrics to your monitor executor:

```python
from prometheus_client import Counter, Histogram, Gauge

monitor_runs = Counter('monitor_runs_total', 'Total monitor runs', ['status'])
monitor_duration = Histogram('monitor_duration_seconds', 'Monitor execution time')
active_monitors = Gauge('active_monitors', 'Number of active monitors')

class MonitorExecutor:
    async def execute_monitor(self, monitor_id: str):
        with monitor_duration.time():
            try:
                result = await self._execute(monitor_id)
                monitor_runs.labels(status='success').inc()
                return result
            except Exception as e:
                monitor_runs.labels(status='failed').inc()
                raise
```

### Logging Configuration

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('websets.log'),
        logging.StreamHandler()
    ]
)

# Set module loggers
logging.getLogger('src.websets').setLevel(logging.INFO)
logging.getLogger('src.monitors').setLevel(logging.INFO)
logging.getLogger('src.enrichments').setLevel(logging.INFO)
```

## Common Patterns

### Pattern 1: Scheduled Search with Enrichment

```python
async def setup_ai_news_monitor():
    manager = WebsetManager()
    await manager.init_db()

    # Create webset
    webset = await manager.create_webset(
        name="AI News Daily",
        search_query="artificial intelligence news",
        entity_type="article"
    )

    # Create monitor with hybrid behavior
    monitor = await manager.create_monitor(
        webset_id=webset.id,
        cron_expression="0 9 * * *",  # Daily at 9 AM
        behavior_type="hybrid",
        behavior_config={
            "search_config": {
                "query": "AI news",
                "top_k": 50,
                "crawl_results": True,
                "store_to_ruvector": True
            },
            "refresh_config": {
                "use_playwright": False,
                "run_enrichments": True,
                "max_items": 100
            }
        },
        timezone="UTC"
    )

    return webset, monitor
```

### Pattern 2: Bulk Content Enrichment

```python
async def enrich_all_items(webset_id: str):
    from src.enrichments import CachedEnrichmentEngine
    from src.enrichments.plugins.content_enricher import ContentSummaryEnricher

    manager = WebsetManager()
    await manager.init_db()

    # Get all items
    items = await manager.get_items(webset_id, limit=1000)

    # Setup enrichment engine
    engine = CachedEnrichmentEngine()
    engine.register_plugin(ContentSummaryEnricher({
        "provider": "openai",
        "model": "gpt-4",
        "max_length": 150
    }))

    # Enrich each item
    for item in items:
        if not item.content:
            continue

        results = await engine.enrich(item.content)

        # Update item
        enrichments = {
            name: result.to_dict()
            for name, result in results.items()
        }
        await manager.update_item(
            item_id=item.id,
            enrichments=enrichments
        )
```

## Troubleshooting

### Common Issues

1. **Database locked**: Use WAL mode for SQLite
   ```python
   # Add to database URL
   "sqlite+aiosqlite:///./data/websets.db?timeout=20"
   ```

2. **Monitor not running**: Check scheduler status
   ```python
   jobs = scheduler.get_jobs()
   for job in jobs:
       print(f"{job.id}: next run at {job.next_run_time}")
   ```

3. **Enrichment failures**: Check API keys
   ```bash
   echo $OPENAI_API_KEY
   echo $ANTHROPIC_API_KEY
   ```

## Next Steps

1. Set up monitoring dashboard
2. Configure backup strategy for database
3. Implement rate limiting for external APIs
4. Add webhook notifications
5. Create custom enrichment plugins for your domain

## Support

For issues and questions:
- Check the [WEBSETS_README.md](./WEBSETS_README.md) for detailed documentation
- Review error logs in `websets.log`
- Monitor scheduler jobs with `scheduler.get_jobs()`
