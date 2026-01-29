# Webset Management and Monitoring System

A comprehensive system for managing, monitoring, and enriching web content collections (websets) with automated scheduling, deduplication, and structured data extraction.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Webset Management System                  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Websets    │  │   Monitors   │  │ Enrichments  │      │
│  │              │  │              │  │              │      │
│  │ • Manager    │  │ • Scheduler  │  │ • Engine     │      │
│  │ • Search     │  │ • Behaviors  │  │ • Plugins    │      │
│  │ • Dedupe     │  │ • Executor   │  │ • Cache      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                 │                   │              │
│         └─────────────────┴───────────────────┘              │
│                           │                                  │
│                    ┌──────▼──────┐                          │
│                    │  SQLAlchemy │                          │
│                    │   Database  │                          │
│                    └─────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Websets Module (`src/websets/`)

#### Manager (`manager.py`)
- **WebsetManager**: Async SQLAlchemy-based CRUD operations
  - Create, read, update, delete websets
  - Manage webset items with content and metadata
  - Monitor creation and management
  - Track monitor runs with statistics

**Models:**
- `Webset`: Collection of web content with search criteria
- `WebsetItem`: Individual web page with content, metadata, and enrichments
- `Monitor`: Scheduled job for webset updates
- `MonitorRun`: Execution history and statistics

**Key Features:**
- Async-first design with aiosqlite
- Automatic content hashing for deduplication
- RuVector integration for vector search
- Full transaction support

#### Search (`search.py`)
- **SearchExecutor**: Execute search queries and process results
  - RuVector hybrid search (semantic + keyword)
  - Web search integration (placeholder for APIs)
  - Concurrent URL crawling with rate limiting
  - Result deduplication and processing

- **SearchQueryBuilder**: Build optimized search queries
  - Entity-based queries (company, person, product)
  - Temporal constraints
  - Query expansion with synonyms

**Key Features:**
- Configurable search strategies
- Automatic crawling and parsing
- Semaphore-based concurrency control
- Metadata extraction from search results

#### Deduplication (`deduplication.py`)
- **ContentDeduplicator**: Hash-based content deduplication
  - SHA256 for exact duplicates
  - SimHash for near-duplicates
  - MinHash for fuzzy matching
  - Content normalization and cleaning

- **URLDeduplicator**: URL normalization and deduplication
  - Protocol and www normalization
  - Tracking parameter removal
  - Case normalization

**Key Features:**
- Multiple hashing strategies
- Configurable similarity thresholds
- Boilerplate removal
- N-gram tokenization

### 2. Monitors Module (`src/monitors/`)

#### Scheduler (`scheduler.py`)
- **MonitorScheduler**: APScheduler-based job scheduling
  - Cron-based scheduling with timezone support
  - SQLite job persistence
  - Async and sync execution modes
  - Job lifecycle management (add, remove, pause, resume)

**Key Features:**
- Job persistence across restarts
- Misfire handling with grace period
- Single instance per job enforcement
- Auto-load existing monitors on startup

#### Behaviors (`behaviors.py`)
- **SearchBehavior**: Find and add new content
  - Execute search queries
  - Crawl and parse results
  - Deduplicate against existing content
  - Store to RuVector

- **RefreshBehavior**: Update existing content
  - Re-crawl existing URLs
  - Detect content changes
  - Update RuVector documents
  - Trigger enrichments on changes

- **HybridBehavior**: Combined search + refresh
  - Two-phase execution
  - Separate configuration for each phase
  - Comprehensive statistics

- **BehaviorFactory**: Create behavior instances by type

**Key Features:**
- Pluggable behavior system
- Comprehensive error handling
- Detailed execution statistics
- RuVector integration

#### Executor (`executor.py`)
- **MonitorExecutor**: Execute monitor jobs with error handling
  - Initialize database and components
  - Execute behaviors with configuration
  - Record run statistics
  - Retry failed runs
  - Test configurations

**Key Features:**
- Comprehensive error logging
- Automatic monitor status updates
- Run history tracking
- Configuration validation

### 3. Enrichments Module (`src/enrichments/`)

#### Engine (`engine.py`)
- **EnrichmentEngine**: Plugin system for content enrichment
  - Register/unregister plugins
  - Execute enrichments in parallel
  - Batch processing
  - Auto-discovery of plugins

- **EnrichmentPipeline**: Multi-stage enrichment
  - Sequential execution
  - Conditional stages
  - Result accumulation

- **CachedEnrichmentEngine**: Engine with result caching
  - In-memory cache
  - Content-hash based keys
  - LRU eviction

**Base Classes:**
- `EnrichmentPlugin`: Base for all enrichment plugins
- `EnrichmentResult`: Standardized result format

#### Plugins (`src/enrichments/plugins/`)

**Company Enricher (`company_enricher.py`)**
- Extract company information:
  - CEO/Founder
  - Revenue
  - Employee count
  - Industry
  - Founded year
  - Headquarters
- Pattern-based and LLM-based extraction
- Financial metrics plugin included

**Person Enricher (`person_enricher.py`)**
- Extract person information:
  - Name
  - Job title
  - Company
  - Location
  - Education
  - Social profiles (LinkedIn, Twitter, GitHub)
  - Contact info (email, phone)
- Experience and skills extraction

**Content Enricher (`content_enricher.py`)**
- LLM-based content enrichment:
  - Summaries with OpenAI/Anthropic
  - Key points extraction
  - Structured data extraction with Instructor
- Fallback to simple methods when LLM unavailable

## Database Schema

```sql
-- Websets table
CREATE TABLE websets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    search_query TEXT,
    search_criteria TEXT,  -- JSON
    entity_type TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Webset items table
CREATE TABLE webset_items (
    id TEXT PRIMARY KEY,
    webset_id TEXT REFERENCES websets(id),
    url TEXT NOT NULL,
    title TEXT,
    content TEXT,
    content_hash TEXT,
    metadata TEXT,  -- JSON
    enrichments TEXT,  -- JSON
    ruvector_doc_id TEXT,
    last_crawled_at TIMESTAMP,
    created_at TIMESTAMP
);

-- Monitors table
CREATE TABLE monitors (
    id TEXT PRIMARY KEY,
    webset_id TEXT REFERENCES websets(id),
    cron_expression TEXT NOT NULL,
    timezone TEXT DEFAULT 'UTC',
    behavior_type TEXT,  -- search, refresh, hybrid
    behavior_config TEXT,  -- JSON
    status TEXT DEFAULT 'enabled',  -- enabled, disabled, error
    last_run_at TIMESTAMP
);

-- Monitor runs table
CREATE TABLE monitor_runs (
    id TEXT PRIMARY KEY,
    monitor_id TEXT REFERENCES monitors(id),
    status TEXT,  -- running, completed, failed
    items_added INTEGER,
    items_updated INTEGER,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);
```

## Usage Examples

### Basic Webset Management

```python
from src.websets import WebsetManager

# Initialize manager
manager = WebsetManager("sqlite+aiosqlite:///./data/websets.db")
await manager.init_db()

# Create a webset
webset = await manager.create_webset(
    name="AI Startups",
    search_query="artificial intelligence startups 2024",
    entity_type="company"
)

# Add items
item = await manager.add_item(
    webset_id=webset.id,
    url="https://example.com/ai-startup",
    title="Amazing AI Startup",
    content="Content here..."
)

# Search for items
items = await manager.get_items(webset.id, limit=50)
```

### Search and Crawl

```python
from src.websets import SearchExecutor

executor = SearchExecutor()

# Execute search and crawl results
results = await executor.search_and_crawl(
    query="machine learning companies",
    search_type="ruvector",
    top_k=10,
    crawl_results=True,
    deduplicate=True
)

# Process results
for result in results:
    print(f"{result.title}: {result.url}")
```

### Monitor Setup

```python
from src.monitors import MonitorScheduler, MonitorExecutor
from src.websets import WebsetManager

# Create monitor
manager = WebsetManager()
await manager.init_db()

monitor = await manager.create_monitor(
    webset_id=webset.id,
    cron_expression="0 */6 * * *",  # Every 6 hours
    behavior_type="hybrid",
    behavior_config={
        "search_config": {
            "query": "AI news",
            "top_k": 20
        },
        "refresh_config": {
            "use_playwright": False,
            "max_items": 100
        }
    },
    timezone="UTC"
)

# Start scheduler
scheduler = await start_scheduler()
```

### Content Enrichment

```python
from src.enrichments import CachedEnrichmentEngine
from src.enrichments.plugins.company_enricher import CompanyEnricher
from src.enrichments.plugins.content_enricher import ContentSummaryEnricher

# Create engine
engine = CachedEnrichmentEngine(cache_size=1000)

# Register plugins
engine.register_plugin(CompanyEnricher())
engine.register_plugin(ContentSummaryEnricher({
    "provider": "openai",
    "model": "gpt-4",
    "max_length": 200
}))

# Enrich content
results = await engine.enrich(
    content="Content to enrich...",
    plugin_names=["CompanyEnricher", "ContentSummaryEnricher"]
)

for plugin_name, result in results.items():
    if result.success:
        print(f"{plugin_name}: {result.data}")
```

### Behavior Execution

```python
from src.monitors import MonitorExecutor

executor = MonitorExecutor()

# Execute monitor
result = await executor.execute_monitor(monitor_id="mon-123")
print(f"Added: {result.items_added}, Updated: {result.items_updated}")

# One-time execution without monitor
result = await executor.execute_webset(
    webset_id="ws-456",
    behavior_type="search",
    behavior_config={"query": "tech news", "top_k": 10}
)
```

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=sqlite+aiosqlite:///./data/websets.db

# RuVector
RUVECTOR_DATA_DIR=./data/ruvector

# LLM APIs
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Crawling
USE_PLAYWRIGHT=0  # Set to 1 to use Playwright
```

### Monitor Cron Expressions

```
# Every hour
0 * * * *

# Every 6 hours
0 */6 * * *

# Daily at midnight
0 0 * * *

# Weekly on Monday
0 0 * * 1

# First day of month
0 0 1 * *
```

## Dependencies

Core:
- `sqlalchemy` - ORM and database management
- `aiosqlite` - Async SQLite driver
- `apscheduler` - Job scheduling
- `httpx` - Async HTTP client
- `playwright` - Browser automation
- `trafilatura` - Content extraction
- `beautifulsoup4` - HTML parsing

Optional:
- `openai` - OpenAI API for enrichments
- `anthropic` - Anthropic API for enrichments
- `instructor` - Structured LLM extraction

## Error Handling

All operations include comprehensive error handling:

1. **Database Errors**: Automatic rollback on transaction failures
2. **Network Errors**: Retry logic with exponential backoff
3. **Parsing Errors**: Graceful fallback to alternative parsers
4. **Enrichment Errors**: Continue processing other plugins
5. **Monitor Errors**: Log errors and update monitor status

## Performance Considerations

1. **Concurrency**: Configurable semaphore limits for crawling
2. **Caching**: In-memory cache for enrichment results
3. **Batching**: Batch processing for large item sets
4. **Indexing**: Database indexes on frequently queried fields
5. **Connection Pooling**: SQLAlchemy connection pool management

## Testing

```bash
# Run all tests
pytest tests/

# Run specific module tests
pytest tests/test_websets.py
pytest tests/test_monitors.py
pytest tests/test_enrichments.py

# Run with coverage
pytest --cov=src tests/
```

## Future Enhancements

- [ ] Webhook notifications for monitor events
- [ ] GraphQL API for webset management
- [ ] Distributed task queue with Celery
- [ ] Real-time websocket updates
- [ ] Advanced analytics and reporting
- [ ] Multi-user support with authentication
- [ ] Custom enrichment plugin marketplace
- [ ] Machine learning-based content classification

## License

MIT
