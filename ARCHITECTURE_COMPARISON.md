# Custom Web Intelligence Pipeline
## Overview
Build a production-grade web extraction and monitoring system using homegrown infrastructure that replicates Firecrawl's extraction, Spark's distributed processing, and Exa's webset monitoring capabilities.
## Architecture Components
### 1. Core Extraction Engine
**Web Crawler Module** (`src/crawler/`)
* Playwright-based headless browser for JS-heavy sites
* Rotating proxy pool with residential IPs
* Smart wait strategies (network idle, DOM mutations)
* Cookie/session management for authenticated content
* Rate limiting per domain with exponential backoff
**Content Parser** (`src/parser/`)
* Trafilatura for main content extraction
* BeautifulSoup4 for structured data (schema.org, Open Graph)
* Custom heuristics for podcast/episode metadata
* Citation tracking system (URL + XPath/CSS selector)
* Multi-format output (Markdown, JSON, HTML)
**LLM-Powered Extraction** (`src/extractors/`)
* Schema-based extraction using Pydantic models
* Prompt-based extraction with structured output
* Requesty.ai LLM router integration for model selection
* Retry logic with fallback models
* Cost tracking per extraction
### 2. Distributed Processing Layer
**Task Queue System** (`src/queue/`)
* Redis-backed Celery for distributed task execution
* Priority queues (realtime, batch, background)
* Result backend for async job status
* Dead letter queue for failed tasks
**Parallel Extraction Workers** (`src/workers/`)
* Multiple worker processes per node
* GPU scheduling for embedding generation
* Memory-efficient batching
* Health checks and auto-restart
**Coordination Service** (`src/coordinator/`)
* Job orchestration and dependency management
* Resource allocation (CPU, GPU, memory)
* Deduplication via content hashing
* Progress tracking and observability
### 3. Data Storage & Retrieval
**SQLite for Operational Data** (`data/sqlite/`)
* Short-term memory (recent extractions, jobs)
* Cron job history and execution logs
* User preferences and API keys
* Fast queries with proper indexing
**RuVector for Knowledge Base** (`src/ruvector/`)
* Self-learning vector database with GNN layers
* Automatic embedding generation (RuvLLM integration)
* Graph queries with Cypher-like syntax
* Hybrid search improving over time
* HNSW index with Q-learning reinforcement
* Horizontal scaling with Raft consensus
* Works offline/edge with WASM support
**Preprocessing Pipeline** (`src/preprocessing/`)
* Content cleaning (boilerplate removal, normalization)
* Smart chunking strategies (semantic, sliding window)
* Metadata extraction and tagging
* Reranking with cross-encoders
### 4. Webset Monitoring System
**Webset Manager** (`src/websets/`)
* SQLite-backed webset definitions
* Search criteria and enrichment configs
* Version control for webset schemas
* Access control and permissions
**Cron Scheduler** (`src/scheduler/`)
* APScheduler for flexible cron expressions
* Timezone-aware scheduling
* Monitor status tracking (enabled/disabled)
* Execution history with retry logic
**Monitor Behaviors** (`src/monitors/`)
* **Search mode**: Run queries, dedupe, append results
* **Refresh mode**: Re-crawl URLs, update enrichments
* **Hybrid mode**: Search + refresh in single run
* Change detection and diff tracking
**Enrichment Engine** (`src/enrichments/`)
* Custom enrichment plugins (CEO name, revenue, etc)
* LLM-based enrichments with prompt templates
* Multi-source aggregation (web + APIs)
* Confidence scoring and validation
## Data Flow
### Extraction Flow
1. **Input**: URL(s) or search query
2. **Crawl**: Fetch content with browser automation
3. **Parse**: Extract structured data + citations
4. **Chunk**: Split into semantic chunks
5. **Embed**: Generate vectors via AstraDB $vectorize
6. **Store**: Save to AstraDB with metadata
7. **Index**: Create hybrid search indexes
### Webset Flow
1. **Define**: Create webset with search criteria
2. **Populate**: Run initial search/extraction
3. **Enrich**: Apply enrichments via LLM
4. **Monitor**: Schedule cron jobs for updates
5. **Notify**: Alert on new/changed entities
## Implementation Details
### Technology Stack
**Backend**: Python 3.11+ with FastAPI
**Frontend**: React + TypeScript + Vite + TailwindCSS + shadcn/ui
**Crawling**: Playwright, httpx, beautifulsoup4, trafilatura
**Processing**: Celery + Redis
**Storage**: SQLite (operational), RuVector (knowledge + self-learning)
**LLM**: Requesty.ai router (OpenAI, Claude, etc)
**Scheduling**: APScheduler
**Monitoring**: Prometheus + Grafana
**Node Management**: Volta for version control
### Key Files
```warp-runnable-command
operationTorque/
├── intelligence-pipeline/          # New web intelligence system
│   ├── backend/
│   │   ├── src/
│   │   │   ├── crawler/
│   │   │   │   ├── browser.py      # Playwright wrapper
│   │   │   │   ├── proxy_pool.py   # Proxy rotation
│   │   │   │   └── rate_limiter.py # Per-domain limits
│   │   │   ├── parser/
│   │   │   │   ├── trafilatura_parser.py
│   │   │   │   ├── metadata_extractor.py
│   │   │   │   └── citation_tracker.py
│   │   │   ├── extractors/
│   │   │   │   ├── schema_extractor.py  # Pydantic-based
│   │   │   │   ├── prompt_extractor.py  # Natural language
│   │   │   │   └── llm_router.py        # Requesty.ai
│   │   │   ├── websets/
│   │   │   │   ├── models.py       # SQLite schemas
│   │   │   │   ├── manager.py      # CRUD operations
│   │   │   │   └── search.py       # Query execution
│   │   │   ├── monitors/
│   │   │   │   ├── scheduler.py    # APScheduler setup
│   │   │   │   ├── behaviors.py    # Search/refresh logic
│   │   │   │   └── enrichments.py  # Enrichment runner
│   │   │   ├── ruvector/
│   │   │   │   ├── client.py       # RuVector client
│   │   │   │   ├── embedder.py     # Embedding generation
│   │   │   │   ├── graph.py        # Graph operations (Cypher-like)
│   │   │   │   └── search.py       # Hybrid retrieval + GNN
│   │   │   ├── preprocessing/
│   │   │   │   ├── chunker.py      # Semantic chunking
│   │   │   │   ├── cleaner.py      # Content cleaning
│   │   │   │   └── reranker.py     # Reranking logic
│   │   │   ├── queue/
│   │   │   │   ├── tasks.py        # Celery tasks
│   │   │   │   └── workers.py      # Worker config
│   │   │   └── api/
│   │   │       ├── main.py         # FastAPI app
│   │   │       ├── routes/         # Endpoint handlers
│   │   │       └── schemas/        # Pydantic models
│   │   ├── pyproject.toml
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── DocumentUpload.tsx
│   │   │   │   ├── WebsetManager.tsx
│   │   │   │   ├── MonitorScheduler.tsx
│   │   │   │   └── EnrichmentConfig.tsx
│   │   │   ├── pages/
│   │   │   │   ├── Dashboard.tsx
│   │   │   │   ├── Websets.tsx
│   │   │   │   └── ContentGeneration.tsx
│   │   │   └── lib/
│   │   │       └── api.ts          # API client
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   └── vite.config.ts
│   ├── data/
│   │   └── websets.db              # SQLite database
│   ├── docker-compose.yml
│   ├── .env.example
│   └── README.md
├── vendor/
│   └── ruvector/                   # Git submodule
│       └── (RuVector repository)
├── .gitignore                      # Updated with intelligence-pipeline ignores
├── src/                            # Existing operationTorque source
├── dist/                           # Build output
└── package.json                    # Root package.json
```
### Database Schemas
**SQLite (Operational)**
```SQL
-- Websets
CREATE TABLE websets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    search_query TEXT,
    search_criteria JSON,
    entity_type TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
-- Webset Items
CREATE TABLE webset_items (
    id TEXT PRIMARY KEY,
    webset_id TEXT,
    url TEXT NOT NULL,
    title TEXT,
    content_hash TEXT,
    metadata JSON,
    enrichments JSON,
    astradb_doc_id TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY (webset_id) REFERENCES websets(id)
);
-- Monitors
CREATE TABLE monitors (
    id TEXT PRIMARY KEY,
    webset_id TEXT,
    cron_expression TEXT NOT NULL,
    timezone TEXT DEFAULT 'UTC',
    behavior_type TEXT,
    behavior_config JSON,
    status TEXT DEFAULT 'enabled',
    last_run_at TIMESTAMP,
    FOREIGN KEY (webset_id) REFERENCES websets(id)
);
-- Monitor Runs
CREATE TABLE monitor_runs (
    id TEXT PRIMARY KEY,
    monitor_id TEXT,
    status TEXT,
    items_added INTEGER,
    items_updated INTEGER,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    FOREIGN KEY (monitor_id) REFERENCES monitors(id)
);
-- Extraction Jobs
CREATE TABLE extraction_jobs (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    status TEXT,
    result JSON,
    error TEXT,
    created_at TIMESTAMP,
    completed_at TIMESTAMP
);
```
**AstraDB (Knowledge Base)**
```json
// Document structure
{
  "_id": "uuid",
  "url": "https://ee.show/episodes/...",
  "source_type": "podcast_episode",
  "title": "Episode Title",
  "content": "Full transcript or content",
  "chunks": [
    {
      "text": "Chunk content",
      "chunk_index": 0,
      "embedding": "$vectorize"
    }
  ],
  "metadata": {
    "host": {...},
    "guests": [...],
    "keywords": [...],
    "published_at": "ISO8601"
  },
  "citations": [
    {"url": "...", "selector": "..."}
  ],
  "extracted_at": "ISO8601",
  "webset_ids": ["webset_123"]
}
```
## Advantages Over Firecrawl/Spark/Websets
### Cost Control
* No per-request API costs
* Self-hosted infrastructure
* LLM routing optimizes model costs
### Customization
* Domain-specific parsers (podcast metadata, etc)
* Custom enrichment logic
* Flexible storage strategies
### Privacy
* All data stays in your infrastructure
* No third-party data sharing
* Audit trail for compliance
### Performance
* Distributed processing for scale
* Hybrid search (lexical + semantic)
* Reranking for accuracy
### Integration
* Direct AstraDB integration
* Brand-specific knowledge bases
* Custom publication workflows
## Testing Strategy
**Unit Tests** (`tests/unit/`)
* Parser accuracy on sample pages
* Enrichment logic validation
* Chunking quality assessment
**Integration Tests** (`tests/integration/`)
* End-to-end extraction flows
* Monitor scheduling and execution
* AstraDB operations
**Performance Tests** (`tests/performance/`)
* Concurrent extraction throughput
* Memory usage under load
* Query latency benchmarks
**Type Safety**
* ts-node for TypeScript validation
* Mypy for Python type checking
* Pydantic for runtime validation
## Deployment
**Docker Compose** for local development
**Kubernetes** for production scale
**CI/CD**: GitHub Actions with automated tests
**Monitoring**: Prometheus metrics, Grafana dashboards
**Logging**: Structured logging with correlation IDs
## RuVector Integration
### Installation
```warp-runnable-command
# Add RuVector as git submodule
cd /Users/breydentaylor/operationTorque
git submodule add https://github.com/ruvnet/ruvector.git vendor/ruvector
git submodule update --init --recursive
# Install RuVector npm packages
cd intelligence-pipeline/backend
npm install ruvector
npm install @ruvector/sona  # SONA learning
npm install @ruvector/ruvllm # LLM orchestration
```
### Python Bindings
```warp-runnable-command
# Install Rust RuVector crates (for Python bindings)
cd vendor/ruvector
cargo build --release
# Python wrapper (in intelligence-pipeline/backend/src/ruvector/)
pip install maturin
maturin develop --manifest-path=../../vendor/ruvector/Cargo.toml
```
### Usage Example
```python
# backend/src/ruvector/client.py
import ruvector
from ruvector import RuVector, EmbeddingConfig
class RuVectorClient:
    def __init__(self, data_dir: str):
        self.db = RuVector(
            data_dir=data_dir,
            enable_gnn=True,  # Self-learning GNN layers
            enable_graph=True # Graph queries
        )
    
    async def insert_document(self, doc_id: str, text: str, metadata: dict):
        # Automatic embedding + HNSW indexing
        await self.db.insert(
            id=doc_id,
            text=text,
            metadata=metadata
        )
    
    async def hybrid_search(self, query: str, top_k: int = 10):
        # Hybrid lexical + semantic search with GNN enhancement
        results = await self.db.search(
            query=query,
            top_k=top_k,
            enable_gnn=True,  # Use learned patterns
            hybrid_alpha=0.7  # 70% semantic, 30% lexical
        )
        return results
    
    async def graph_query(self, cypher: str):
        # Graph queries (Cypher-like syntax)
        return await self.db.query(cypher)
```
## gitignore Updates
Add to `/Users/breydentaylor/operationTorque/.gitignore`:
```gitignore
# Intelligence Pipeline
intelligence-pipeline/data/*.db
intelligence-pipeline/data/*.sqlite*
intelligence-pipeline/backend/.venv/
intelligence-pipeline/backend/**/__pycache__/
intelligence-pipeline/backend/*.pyc
intelligence-pipeline/frontend/node_modules/
intelligence-pipeline/frontend/dist/
intelligence-pipeline/.env
intelligence-pipeline/**/.env.local
# RuVector data (keep config, ignore runtime data)
vendor/ruvector/target/
vendor/ruvector/**/.git/
intelligence-pipeline/data/ruvector/*.hnswlib
intelligence-pipeline/data/ruvector/*.index
intelligence-pipeline/data/ruvector/learned_patterns/
# Celery
intelligence-pipeline/backend/celerybeat-schedule
intelligence-pipeline/backend/celerybeat.pid
# Redis dumps
intelligence-pipeline/data/dump.rdb
# Playwright browsers
intelligence-pipeline/backend/.ms-playwright/
```
## Next Steps
1. **Initialize substructure**
```warp-runnable-command
cd /Users/breydentaylor/operationTorque
mkdir -p intelligence-pipeline/{backend/src,frontend/src,data}
mkdir -p vendor
```
2. **Add RuVector submodule**
```warp-runnable-command
git submodule add https://github.com/ruvnet/ruvector.git vendor/ruvector
```
3. **Update .gitignore**
```warp-runnable-command
cat >> .gitignore << 'EOF'
# Intelligence Pipeline (see plan for full list)
intelligence-pipeline/data/*.db
vendor/ruvector/target/
EOF
```
4. **Set up Python backend with Volta**
```warp-runnable-command
cd intelligence-pipeline/backend
volta pin node@22
python3.11 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn playwright trafilatura beautifulsoup4 celery redis
```
5. **Initialize frontend with Vite**
```warp-runnable-command
cd ../frontend
npm create vite@latest . -- --template react-ts
npm install
npx shadcn-ui@latest init
```
6. **Build core crawler with Playwright**
7. **Integrate RuVector for vector storage**
8. **Build extraction engine with LLM router**
9. **Create SQLite schemas for websets**
10. **Build monitor scheduler with APScheduler**
11. **Develop React frontend components**
12. **Add comprehensive test suite**
13. **Deploy with Docker Compose**
14. **Benchmark against ee.show example dataplease use** [https://docs.requesty.ai/quickstart](https://docs.requesty.ai/quickstart)
