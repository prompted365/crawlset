# Backend Infrastructure Setup

This document describes the backend infrastructure that has been created for the intelligence pipeline.

## Overview

A complete, production-ready backend infrastructure with:
- **Async SQLAlchemy** models and database management
- **Pydantic** schemas for API validation
- **FastAPI** application with CORS, error handling, and health checks
- **Type-safe** configuration management using pydantic-settings
- Full **async/await** patterns throughout

## Directory Structure

```
backend/
├── src/
│   ├── __init__.py                    # Package root
│   ├── config.py                      # Configuration management
│   ├── database/
│   │   ├── __init__.py               # Database exports
│   │   ├── models.py                 # SQLAlchemy models
│   │   └── connection.py             # Session management
│   └── api/
│       ├── main.py                   # FastAPI application
│       └── schemas/
│           ├── __init__.py           # Schema exports
│           ├── webset.py             # Webset schemas
│           ├── monitor.py            # Monitor schemas
│           └── extraction.py         # Extraction job schemas
├── requirements.txt                   # Python dependencies
├── verify_setup.py                   # Verification script
└── BACKEND_SETUP.md                  # This file
```

## Components Created

### 1. SQLAlchemy Models (`src/database/models.py`)

All database tables as async SQLAlchemy models:

- **Webset**: Collections of web content with search criteria
- **WebsetItem**: Individual items within a webset
- **Monitor**: Scheduled monitoring tasks with cron expressions
- **MonitorRun**: Execution history for monitors
- **ExtractionJob**: Web extraction task tracking

**Features:**
- Proper relationships with cascade deletes
- JSON column support for metadata
- Timezone-aware datetime fields
- Foreign key constraints
- String representations for debugging

### 2. Database Connection (`src/database/connection.py`)

Async database session management with:

- `DatabaseManager`: Manages engine and session lifecycle
- `init_database()`: Global initialization function
- `get_db_session()`: FastAPI dependency for routes
- Proper async context managers
- Connection pooling (NullPool for SQLite)
- Transaction rollback on errors

**Usage Example:**
```python
from src.database import get_db_session
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

@app.get("/items")
async def get_items(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Webset))
    return result.scalars().all()
```

### 3. Pydantic Schemas (`src/api/schemas/`)

Type-safe request/response schemas for all models:

**Webset Schemas:**
- `WebsetCreate`: Creating new websets
- `WebsetUpdate`: Updating existing websets
- `WebsetResponse`: API responses
- `WebsetItemCreate`: Creating webset items
- `WebsetItemResponse`: Webset item responses

**Monitor Schemas:**
- `MonitorCreate`: Creating new monitors
- `MonitorUpdate`: Updating monitors
- `MonitorResponse`: Monitor responses
- `MonitorRunCreate`: Recording monitor executions
- `MonitorRunResponse`: Monitor run responses

**Extraction Schemas:**
- `ExtractionJobCreate`: Creating extraction jobs
- `ExtractionJobUpdate`: Updating job status
- `ExtractionJobResponse`: Job status responses

**Features:**
- Field validation with descriptions
- Optional fields properly typed
- `from_attributes=True` for ORM compatibility
- JSON field support for metadata

### 4. Configuration (`src/config.py`)

Type-safe configuration using `pydantic-settings`:

**Configuration Areas:**
- Server (host, port, debug, reload)
- Database (URL, echo logging)
- CORS (origins, credentials, methods, headers)
- RuVector (data directory)
- Redis (connection URL)
- Requesty AI (base URL, API key, default model)
- Crawler (headless mode, timeout, user agent)
- Monitoring (scheduler timezone)
- Logging (log level)

**Features:**
- Environment variable support (`.env` file)
- Type validation and conversion
- SQLite URL auto-conversion to async driver
- Singleton pattern for global settings
- Computed properties (e.g., `sqlite_path`)

**Usage Example:**
```python
from src.config import get_settings

settings = get_settings()
print(settings.database_url)  # sqlite+aiosqlite:///./data/websets.db
```

### 5. FastAPI Application (`src/api/main.py`)

Production-ready FastAPI app with:

**Middleware:**
- CORS with configurable origins
- Global exception handlers
- Request/response logging ready

**Lifecycle Management:**
- Async lifespan context manager
- Database initialization on startup
- Proper cleanup on shutdown
- Ready for scheduler integration

**Error Handling:**
- HTTP exception handler with consistent format
- General exception handler with logging
- 500 errors properly logged

**Endpoints:**
- `/health` - Health check with database connectivity
- API routers mounted:
  - `/websets` - Webset management
  - `/crawl` - Web crawling
  - `/extract` - Content extraction
  - `/tools` - Utility tools

**Features:**
- OpenAPI docs auto-generated
- Async/await throughout
- Type hints everywhere
- Proper error responses

## Database Schema

### Tables

All tables match the specification from the Intelligence Pipeline plan:

```sql
-- Websets
CREATE TABLE websets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    search_query TEXT,
    search_criteria JSON,
    entity_type TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Webset Items
CREATE TABLE webset_items (
    id TEXT PRIMARY KEY,
    webset_id TEXT REFERENCES websets(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT,
    content_hash TEXT,
    metadata JSON,
    enrichments JSON,
    astradb_doc_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE
);

-- Monitors
CREATE TABLE monitors (
    id TEXT PRIMARY KEY,
    webset_id TEXT REFERENCES websets(id) ON DELETE CASCADE,
    cron_expression TEXT NOT NULL,
    timezone TEXT DEFAULT 'UTC',
    behavior_type TEXT,
    behavior_config JSON,
    status TEXT DEFAULT 'enabled',
    last_run_at TIMESTAMP WITH TIME ZONE
);

-- Monitor Runs
CREATE TABLE monitor_runs (
    id TEXT PRIMARY KEY,
    monitor_id TEXT REFERENCES monitors(id) ON DELETE CASCADE,
    status TEXT,
    items_added INTEGER,
    items_updated INTEGER,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT
);

-- Extraction Jobs
CREATE TABLE extraction_jobs (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    status TEXT,
    result JSON,
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);
```

## Type Safety

All code is fully typed for mypy compatibility:

- Type hints on all function signatures
- Proper `Optional` and `Union` types
- Generic types for collections
- Pydantic models for validation
- SQLAlchemy 2.0 typed API

## Environment Configuration

Create a `.env` file in the backend directory:

```bash
# Server
PORT=8080
DEBUG=false
RELOAD=true

# Database
DATABASE_URL=sqlite+aiosqlite:///./data/websets.db
DATABASE_ECHO=false

# CORS
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# RuVector
RUVECTOR_DATA_DIR=./data/ruvector

# Redis
REDIS_URL=redis://localhost:6379/0

# Requesty AI
REQUESTY_BASE_URL=https://router.requesty.ai/v1
REQUESTY_API_KEY=your-api-key-here
REQUESTY_DEFAULT_MODEL=google/gemini-2.5-flash

# Crawler
PLAYWRIGHT_HEADLESS=true
CRAWLER_TIMEOUT=30000

# Logging
LOG_LEVEL=INFO
```

## Running the Application

### 1. Verify Setup

```bash
cd /Users/breydentaylor/operationTorque/intelligence-pipeline/backend
python3 verify_setup.py
```

This will validate:
- All imports work correctly
- Settings load properly
- Database models are configured
- Pydantic schemas validate

### 2. Start the Server

```bash
# Development mode with auto-reload
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8080

# Production mode
uvicorn src.api.main:app --host 0.0.0.0 --port 8080 --workers 4
```

### 3. Access Documentation

- API Docs (Swagger): http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc
- Health Check: http://localhost:8080/health

## Testing the API

### Health Check

```bash
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected"
}
```

### Example API Calls

```bash
# Create a webset
curl -X POST http://localhost:8080/websets \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test-webset",
    "name": "Test Webset",
    "entity_type": "podcast",
    "search_query": "tech podcasts"
  }'

# Get all websets
curl http://localhost:8080/websets

# Create a monitor
curl -X POST http://localhost:8080/websets/test-webset/monitors \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test-monitor",
    "cron_expression": "0 */6 * * *",
    "behavior_type": "search",
    "status": "enabled"
  }'
```

## Integration Points

The backend is ready to integrate with:

1. **Existing Routes**: Already includes router imports for:
   - `/websets` - Webset CRUD operations
   - `/crawl` - Web crawling endpoints
   - `/extract` - Content extraction
   - `/tools` - Utility endpoints

2. **RuVector**: Configuration and path setup ready
3. **Celery/Redis**: Task queue configuration prepared
4. **Requesty AI**: LLM router configuration ready
5. **Monitors**: Scheduler integration prepared (TODO in lifespan)

## Next Steps

1. **Implement API Routes**: Update existing route handlers to use new database layer
2. **Add Alembic Migrations**: Set up database migration management
3. **Add Tests**: Create pytest tests for models, schemas, and endpoints
4. **Enable Scheduler**: Uncomment and integrate monitor scheduler in lifespan
5. **Add Authentication**: Implement JWT or API key auth if needed
6. **Add Logging**: Configure structured logging with correlation IDs
7. **Add Metrics**: Integrate Prometheus metrics collection

## Files Created

1. `/Users/breydentaylor/operationTorque/intelligence-pipeline/backend/src/database/models.py`
2. `/Users/breydentaylor/operationTorque/intelligence-pipeline/backend/src/database/connection.py`
3. `/Users/breydentaylor/operationTorque/intelligence-pipeline/backend/src/database/__init__.py`
4. `/Users/breydentaylor/operationTorque/intelligence-pipeline/backend/src/api/schemas/webset.py`
5. `/Users/breydentaylor/operationTorque/intelligence-pipeline/backend/src/api/schemas/monitor.py`
6. `/Users/breydentaylor/operationTorque/intelligence-pipeline/backend/src/api/schemas/extraction.py`
7. `/Users/breydentaylor/operationTorque/intelligence-pipeline/backend/src/api/schemas/__init__.py`
8. `/Users/breydentaylor/operationTorque/intelligence-pipeline/backend/src/config.py`
9. `/Users/breydentaylor/operationTorque/intelligence-pipeline/backend/src/__init__.py`
10. `/Users/breydentaylor/operationTorque/intelligence-pipeline/backend/src/api/main.py` (updated)
11. `/Users/breydentaylor/operationTorque/intelligence-pipeline/backend/verify_setup.py`
12. `/Users/breydentaylor/operationTorque/intelligence-pipeline/backend/BACKEND_SETUP.md` (this file)

## Notes

- All code follows async/await patterns for optimal performance
- Type hints are comprehensive for mypy compatibility
- Error handling is consistent and production-ready
- Database relationships properly configured with cascade deletes
- Configuration is environment-aware and type-safe
- CORS is properly configured for frontend integration
