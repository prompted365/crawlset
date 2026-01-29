# Quick Start Guide - Intelligence Pipeline

Get up and running in 5 minutes.

## Prerequisites

- Python 3.11+
- Node.js 22+
- Redis (via Docker or local)

## Setup (5 steps)

### 1. Install Dependencies

```bash
# Backend
cd /Users/breydentaylor/operationTorque/intelligence-pipeline/backend
pip install -r requirements.txt
playwright install chromium chromium-deps

# Frontend
cd ../frontend
npm install
```

### 2. Start Redis

```bash
docker run -d --name intelligence-redis -p 6379:6379 redis:7-alpine
```

### 3. Configure Environment

```bash
cd /Users/breydentaylor/operationTorque/intelligence-pipeline
cp .env.example .env
```

**Edit `.env` and add your API key**:
```env
REQUESTY_API_KEY=your_requesty_key_here
# OR
OPENAI_API_KEY=your_openai_key_here
```

### 4. Initialize Database

```bash
cd backend
python -c "import asyncio; from src.database import init_database; asyncio.run(init_database())"
```

### 5. Start Services

Open 3 terminal windows:

**Terminal 1 - Backend**:
```bash
cd /Users/breydentaylor/operationTorque/intelligence-pipeline/backend
uvicorn src.api.main:app --reload --port 8000
```

**Terminal 2 - Celery Worker**:
```bash
cd /Users/breydentaylor/operationTorque/intelligence-pipeline/backend
celery -A src.queue.celery_app worker -Q realtime,batch,background -l info
```

**Terminal 3 - Frontend**:
```bash
cd /Users/breydentaylor/operationTorque/intelligence-pipeline/frontend
npm run dev
```

## Access

- **Frontend UI**: http://localhost:3000 (or :3001 if 3000 is busy)
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## First Steps

### 1. Extract a Web Page

**Via UI**:
1. Open http://localhost:3000
2. Click "Extraction" tab
3. Enter a URL (try: https://news.ycombinator.com)
4. Click "Extract"
5. View results in "Extraction Jobs" tab

**Via API**:
```bash
curl -X POST http://localhost:8000/api/extraction/extract \
  -H "Content-Type: application/json" \
  -d '{"url": "https://news.ycombinator.com"}'
```

### 2. Create a Webset

**Via UI**:
1. Click "Websets" tab
2. Click "Create Webset"
3. Fill in:
   - Name: "Tech News"
   - Search Query: "artificial intelligence news"
   - Entity Type: "article"
4. Click "Save"

**Via API**:
```bash
curl -X POST http://localhost:8000/api/websets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tech News",
    "search_query": "artificial intelligence news",
    "entity_type": "article"
  }'
```

### 3. Search Content

**Via UI**:
1. Click "Search" tab
2. Enter query: "machine learning"
3. Select search mode (hybrid recommended)
4. View results

**Via API**:
```bash
curl -X POST http://localhost:8000/api/search/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning",
    "mode": "hybrid",
    "top_k": 10
  }'
```

### 4. Set Up a Monitor

**Via UI**:
1. Click "Monitors" tab
2. Click "Create Monitor"
3. Select webset
4. Set cron: "0 */6 * * *" (every 6 hours)
5. Choose behavior: "search" or "hybrid"
6. Click "Create"

**Via API**:
```bash
curl -X POST http://localhost:8000/api/monitors \
  -H "Content-Type: application/json" \
  -d '{
    "webset_id": "your-webset-id",
    "cron_expression": "0 */6 * * *",
    "behavior_type": "hybrid",
    "timezone": "UTC"
  }'
```

## Common Tasks

### Extract Multiple URLs

```python
import asyncio
from src.queue.tasks import batch_extract_task

urls = [
    "https://example.com/page1",
    "https://example.com/page2",
    "https://example.com/page3"
]

# Submit batch task
result = batch_extract_task.delay(urls)

# Wait for result
data = result.get(timeout=300)
print(f"Extracted {len(data['results'])} pages")
```

### Search with Filters

```bash
curl -X POST http://localhost:8000/api/search/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "AI startups",
    "mode": "hybrid",
    "filters": {
      "webset_ids": ["webset-123"],
      "entity_type": "company",
      "date_range": {
        "start": "2024-01-01",
        "end": "2024-12-31"
      }
    },
    "top_k": 20
  }'
```

### Enrich Webset Items

```bash
curl -X POST http://localhost:8000/api/enrichments/websets/your-webset-id/enrich \
  -H "Content-Type: application/json" \
  -d '{
    "plugins": ["company_enricher", "content_enricher"]
  }'
```

### Export Webset

```bash
# As JSON
curl http://localhost:8000/api/export/websets/your-webset-id/json > webset.json

# As CSV
curl http://localhost:8000/api/export/websets/your-webset-id/csv > webset.csv

# As Markdown
curl http://localhost:8000/api/export/websets/your-webset-id/markdown > webset.md
```

## Python SDK Examples

### Extract and Process Content

```python
import asyncio
from src.crawler import PlaywrightBrowser
from src.parser import parse_html, extract_metadata
from src.extractors import SchemaExtractor, Person

async def extract_person_info(url: str):
    # Crawl page
    async with PlaywrightBrowser() as browser:
        result = await browser.fetch(url)

    # Parse content
    parsed = await parse_html(result['html'], url)
    metadata = await extract_metadata(result['html'], url)

    # Extract structured data
    extractor = SchemaExtractor()
    people = await extractor.extract(
        parsed['text'],
        schema=Person,
        multiple=True
    )

    return {
        'content': parsed,
        'metadata': metadata,
        'people': people
    }

# Run
result = asyncio.run(extract_person_info("https://example.com/team"))
print(f"Found {len(result['people'])} people")
```

### Create and Populate Webset

```python
import asyncio
from src.websets import WebsetManager
from src.ruvector import create_client

async def create_ai_companies_webset():
    # Initialize
    manager = WebsetManager()
    await manager.init_db()

    # Create webset
    webset = await manager.create_webset(
        name="AI Companies",
        search_query="artificial intelligence companies 2024",
        entity_type="company"
    )

    # Add items
    urls = [
        "https://openai.com",
        "https://anthropic.com",
        "https://cohere.com"
    ]

    for url in urls:
        await manager.add_item(
            webset_id=webset.id,
            url=url,
            metadata={"source": "manual"}
        )

    print(f"Created webset: {webset.id}")
    return webset

webset = asyncio.run(create_ai_companies_webset())
```

### Set Up Automated Monitoring

```python
import asyncio
from src.monitors import start_scheduler, create_monitor

async def setup_daily_monitor(webset_id: str):
    # Start scheduler
    scheduler = await start_scheduler()

    # Create monitor (runs daily at 9 AM)
    monitor = await create_monitor(
        webset_id=webset_id,
        cron_expression="0 9 * * *",
        behavior_type="hybrid",
        behavior_config={
            "search_query": "AI news",
            "max_results": 50,
            "refresh_existing": True
        }
    )

    print(f"Monitor created: {monitor.id}")
    print(f"Next run: {monitor.next_run_time}")

    # Keep scheduler running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        scheduler.shutdown()

asyncio.run(setup_daily_monitor("your-webset-id"))
```

## Monitoring & Debugging

### View Celery Tasks

```bash
# Install flower
pip install flower

# Start flower
celery -A src.queue.celery_app flower

# Access: http://localhost:5555
```

### Check Logs

```bash
# Backend logs (in terminal)
# Celery worker logs (in terminal)

# Or use structured logging
tail -f logs/backend.log
tail -f logs/celery.log
```

### Database Inspection

```bash
# SQLite CLI
sqlite3 data/websets.db

# List tables
.tables

# View websets
SELECT * FROM websets;

# View items
SELECT id, url, title FROM webset_items LIMIT 10;
```

## Troubleshooting

### Playwright Issues

```bash
# Reinstall browsers
playwright install --force chromium
playwright install-deps
```

### Redis Connection Issues

```bash
# Check Redis is running
docker ps | grep redis

# Test connection
redis-cli ping
```

### Import Errors

```bash
# Ensure you're in the backend directory
cd /Users/breydentaylor/operationTorque/intelligence-pipeline/backend

# Run Python from backend directory
python -c "from src.api.main import app; print('OK')"
```

### Frontend Build Issues

```bash
# Clear cache and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
```

## Next Steps

1. **Read the full docs**: See SYSTEM_SUMMARY.md for all features
2. **Configure advanced features**: Edit .env for proxy pools, custom models
3. **Create custom enrichers**: See src/enrichments/plugins/ for examples
4. **Set up production**: Use docker-compose.yml for deployment
5. **Explore the API**: http://localhost:8000/docs

## Getting Help

- **Documentation**: See /docs folder
- **API Reference**: http://localhost:8000/docs
- **Examples**: See src/*/example_*.py files

---

You're now running a production-grade intelligence pipeline! 🚀
