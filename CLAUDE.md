# CLAUDE.md - Guide for AI Agents

This file helps AI agents (like Claude) understand the Crawlset repository structure, architecture, and contribution patterns.

## What is Crawlset?

Crawlset is a self-hosted web intelligence pipeline that combines:
- Advanced web crawling (like Firecrawl)
- Webset collections (like Exa)
- Distributed processing (like Spark)
- Vector search ([RuVector](https://github.com/ruvnet/ruvector))

No vendor lock-in, no API costs, full control.

## Repository Structure

```
crawlset/
├── backend/            # Python 3.11+ FastAPI application
│   ├── src/
│   │   ├── api/       # REST endpoints (50+ routes)
│   │   ├── crawler/   # Playwright browser automation
│   │   ├── parser/    # Content extraction (Trafilatura, BeautifulSoup)
│   │   ├── extractors/# LLM-powered extraction
│   │   ├── websets/   # Collection management
│   │   ├── monitors/  # Cron-based monitoring
│   │   ├── enrichments/# Plugin system for data enrichment
│   │   ├── queue/     # Celery task queue
│   │   ├── ruvector/  # RuVector async HTTP client
│   │   ├── preprocessing/# Content chunking, cleaning, reranking
│   │   └── database/  # SQLAlchemy models
│   └── requirements.txt
├── frontend/          # React 19 + TypeScript + Vite
│   ├── src/
│   │   ├── components/# 40+ React components
│   │   ├── pages/     # 6 main pages
│   │   └── lib/       # API client, hooks, utils
│   └── package.json
├── docs/              # Documentation
├── marketing/         # Launch materials
└── docker-compose.yml # Full stack deployment
```

## Key Concepts

### 1. Websets
Collections of web content organized by topic/entity. Like playlists for web pages.

**Database**: `websets` table (SQLite)
**Vector Storage**: RuVector collections
**Code**: `backend/src/websets/manager.py`

### 2. Extraction Jobs
Async tasks that crawl and extract content from URLs.

**Queue**: Celery with 3 priorities (realtime, batch, background)
**Code**: `backend/src/queue/tasks.py`
**API**: `/api/extraction/*`

### 3. Monitors
Cron jobs that run on schedules to find new content or refresh existing items.

**Scheduler**: APScheduler
**Behaviors**: Search, Refresh, Hybrid
**Code**: `backend/src/monitors/`

### 4. Enrichments
Plugins that add metadata/insights to extracted content using LLMs.

**Plugins**: Company, Person, Content enrichers
**Code**: `backend/src/enrichments/plugins/`

### 5. Hybrid Search
Combines vector similarity (RuVector HNSW + GNN) + keyword matching (BM25) for better results.

**Vector DB**: [RuVector](https://github.com/ruvnet/ruvector) (Rust/Axum on port 6333)
**Code**: `backend/src/ruvector/search.py`

## Architecture Patterns

### Async Everywhere
All I/O operations use `async/await`:
```python
async def fetch_url(url: str) -> dict:
    async with PlaywrightBrowser() as browser:
        return await browser.fetch(url)
```

### Dependency Injection
FastAPI routes use DI for database sessions:
```python
@router.get("/websets")
async def list_websets(db: AsyncSession = Depends(get_db_session)):
    return await WebsetManager(db).list_all()
```

### Task Queue Pattern
Long-running operations go through Celery:
```python
# In API route
job_id = extract_url_task.delay(url)
return {"job_id": job_id}

# In Celery task
@app.task(bind=True)
def extract_url_task(self, url: str):
    # Do work
    return result
```

### Plugin Architecture
Enrichments use a plugin system:
```python
class BaseEnricher:
    def enrich(self, item: WebsetItem) -> dict:
        raise NotImplementedError

# Plugins auto-discovered in enrichments/plugins/
```

## Code Style

### Python (Backend)
- **Formatter**: `black` (line length: 100)
- **Linter**: `ruff`
- **Type Checking**: `mypy --strict`
- **Imports**: Absolute imports from `src.*`
- **Async**: Always use `async/await` for I/O

Example:
```python
from src.database import get_db_session
from src.websets import WebsetManager

async def create_webset(name: str, db: AsyncSession) -> Webset:
    """Create a new webset collection."""
    manager = WebsetManager(db)
    return await manager.create(name=name)
```

### TypeScript (Frontend)
- **Formatter**: `prettier`
- **Linting**: ESLint
- **Imports**: Use `@/*` aliases
- **Components**: Functional components with hooks
- **State**: React Query for server state

Example:
```typescript
import { useWebsets } from '@/lib/hooks'
import { WebsetList } from '@/components/websets/WebsetList'

export function Websets() {
  const { data: websets = [], isLoading } = useWebsets()

  if (isLoading) return <div>Loading...</div>
  return <WebsetList websets={websets} />
}
```

## Common Tasks

### Adding an API Endpoint

1. Create route in `backend/src/api/routes/`:
```python
@router.post("/websets/{id}/refresh")
async def refresh_webset(
    id: str,
    db: AsyncSession = Depends(get_db_session)
) -> dict:
    manager = WebsetManager(db)
    await manager.refresh(id)
    return {"status": "success"}
```

2. Add to `main.py`:
```python
app.include_router(websets.router, prefix="/api/websets", tags=["websets"])
```

3. Update frontend API client in `frontend/src/lib/api.ts`:
```typescript
async refreshWebset(websetId: string): Promise<void> {
  return this.request(`/api/websets/${websetId}/refresh`, {
    method: 'POST'
  })
}
```

### Adding an Enrichment Plugin

1. Create file in `backend/src/enrichments/plugins/my_enricher.py`:
```python
from src.enrichments.engine import BaseEnricher

class MyEnricher(BaseEnricher):
    name = "my_enricher"

    async def enrich(self, item: WebsetItem) -> dict:
        # Your logic here
        return {"custom_field": "value"}
```

2. Plugin auto-discovered - no registration needed!

3. Use it:
```python
engine = EnrichmentEngine()
result = await engine.run_enrichment(item, "my_enricher")
```

### Adding a Frontend Component

1. Create component in `frontend/src/components/`:
```typescript
// frontend/src/components/MyComponent.tsx
import { Card } from '@/components/ui/card'

export function MyComponent() {
  return <Card>Hello</Card>
}
```

2. Use it in a page:
```typescript
import { MyComponent } from '@/components/MyComponent'

export function MyPage() {
  return <MyComponent />
}
```

## Testing

### Backend Tests
```bash
# Run all tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific test
pytest tests/test_websets.py::test_create_webset
```

### Frontend Tests
```bash
# Run tests
npm test

# With coverage
npm test -- --coverage
```

### Integration Tests
```bash
# Full stack test
docker-compose -f docker-compose.test.yml up
```

## Integration Points

### RuVector Integration
Location: `backend/src/ruvector/`
- **Client**: `client.py` - Async HTTP client (httpx) to Rust/Axum server on port 6333
- **Embedder**: `embedder.py` - sentence-transformers with Redis caching
- **Search**: `search.py` - Hybrid search (HNSW vector + BM25 + GNN-enhanced)
- **Graph**: `graph.py` - Cypher graph queries for entity relationships

RuVector is a Rust-based self-learning vector database designed by [Ruv](https://github.com/ruvnet/ruvector). It features HNSW indexing, GNN self-learning, SONA optimization, and Cypher graph queries. It runs as a single service (replacing the 3-service Milvus stack of etcd + MinIO + standalone) with 61us p50 latency and 200MB per 1M vectors.

Key operations:
```python
from src.ruvector.client import RuVectorClient

client = RuVectorClient(ruvector_url="http://localhost:6333")
await client.initialize()
await client.insert_document(doc_id="doc1", text="...", metadata={...})
results = await client.hybrid_search("query text", top_k=10)
graph_results = await client.graph_query("MATCH (a)-[:RELATED_TO]->(b) RETURN a, b")
await client.close()
```

### Celery Tasks
Location: `backend/src/queue/`

Three priority levels:
- **realtime**: User-facing operations (4 workers)
- **batch**: Bulk processing (2 workers)
- **background**: Cleanup, maintenance (1 worker)

### Database
**Operational**: SQLite (or PostgreSQL in production)
**Vector**: RuVector collections (Rust/Axum on port 6333)

Models in `backend/src/database/models.py`

## Git Workflow

1. Create feature branch from `main`
2. Make changes
3. Run tests locally
4. Commit with descriptive message
5. Push and create PR
6. Wait for CI checks
7. Address review comments
8. Merge when approved

## Environment Setup

### Backend
```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### Frontend
```bash
cd frontend
npm install
```

### Full Stack
```bash
cp .env.example .env
# Add API keys
docker-compose up -d
```

## Configuration

All config in `.env`:
- **Required**: LLM API key (Requesty/OpenAI/Anthropic)
- **Required**: Redis URL
- **Required**: RuVector host (default: localhost:6333)
- **Optional**: Proxy URLs, rate limits, etc.

See `.env.example` for all options.

## Debugging

### Backend Logs
```bash
docker-compose logs -f backend
```

### Celery Tasks
```bash
# Flower UI
open http://localhost:5555

# Or CLI
docker-compose exec backend celery -A src.queue.celery_app inspect active
```

### Database
```bash
# SQLite
sqlite3 data/websets.db
.tables
SELECT * FROM websets;

# RuVector
curl http://localhost:6333/health
curl http://localhost:6333/collections
```

## Performance Considerations

- **Async I/O**: Never use blocking calls
- **Batch Operations**: Bulk insert > individual inserts
- **Caching**: Use Redis for computed embeddings
- **Connection Pooling**: Reuse database connections
- **Worker Scaling**: Scale Celery workers horizontally

## Security

- Never commit `.env` files
- Never commit API keys
- Always validate user input
- Use parameterized SQL queries (SQLAlchemy handles this)
- Rate limit API endpoints
- Sanitize URLs before crawling

## When Contributing

**Good first issues**:
- Add new enrichment plugin
- Add new parser for specific site type
- Improve error messages
- Add tests for existing features
- Improve documentation

**Before submitting PR**:
- [ ] Tests pass (`pytest` and `npm test`)
- [ ] Code formatted (`black` and `prettier`)
- [ ] Type hints added (Python)
- [ ] Docstrings added for new functions
- [ ] No secrets in code
- [ ] CHANGELOG.md updated

## Questions?

- Check existing docs in `docs/`
- Read related code in the module
- Check GitHub issues for similar questions
- Ask in PR/issue if still unclear

## Useful Commands

```bash
# Backend type check
mypy backend/src

# Backend format
black backend/src
ruff check backend/src

# Frontend format
cd frontend && npm run format

# Build docs
cd docs && make html

# Reset database
rm data/websets.db
docker-compose restart backend

# Scale workers
docker-compose up -d --scale celery-worker-realtime=3
```

---

This guide covers the essentials. For deeper dives, see:
- [System Summary](SYSTEM_SUMMARY.md) - Complete architecture
- [API Routes](backend/API_ROUTES.md) - All endpoints
- [RuVector Integration](docs/RUVECTOR_INTEGRATION.md) - Vector database integration
- [Contributing](CONTRIBUTING.md) - Contribution guidelines
