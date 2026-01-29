# API Routes Implementation Instructions

## Location
`/Users/breydentaylor/operationTorque/intelligence-pipeline/backend/src/api/routes/`

## Files to Create

### 1. `websets.py`
Complete CRUD for websets:
- POST /api/websets - Create webset (name, search_query, search_criteria, entity_type)
- GET /api/websets - List all websets (with pagination, filters)
- GET /api/websets/{id} - Get single webset with stats
- PATCH /api/websets/{id} - Update webset
- DELETE /api/websets/{id} - Delete webset and all items
- GET /api/websets/{id}/items - List items in webset (paginated)
- POST /api/websets/{id}/items - Add item to webset
- DELETE /api/websets/{id}/items/{item_id} - Remove item
- POST /api/websets/{id}/search - Execute search and populate
- GET /api/websets/{id}/stats - Statistics (item count, last updated, etc)

### 2. `extraction.py`
Extraction job endpoints:
- POST /api/extraction/extract - Submit URL for extraction (returns job_id)
- POST /api/extraction/batch - Submit multiple URLs
- GET /api/extraction/jobs/{job_id} - Get job status
- GET /api/extraction/jobs - List all jobs (with filters)
- DELETE /api/extraction/jobs/{job_id} - Cancel/delete job
- GET /api/extraction/jobs/{job_id}/result - Get extraction result
- POST /api/extraction/crawl - Full crawl with parsing (sync for simple pages)

### 3. `monitors.py`
Monitor management:
- POST /api/monitors - Create monitor (webset_id, cron, behavior_type, config)
- GET /api/monitors - List all monitors
- GET /api/monitors/{id} - Get monitor details
- PATCH /api/monitors/{id} - Update monitor (cron, config, status)
- DELETE /api/monitors/{id} - Delete monitor
- POST /api/monitors/{id}/trigger - Trigger monitor run manually
- GET /api/monitors/{id}/runs - List monitor runs (history)
- GET /api/monitors/{id}/runs/{run_id} - Get run details

### 4. `enrichments.py`
Enrichment endpoints:
- POST /api/enrichments/enrich - Enrich a webset item
- POST /api/enrichments/batch - Batch enrich multiple items
- GET /api/enrichments/plugins - List available enrichment plugins
- GET /api/enrichments/plugins/{plugin_id} - Plugin details
- POST /api/websets/{id}/enrich - Enrich all items in webset

### 5. `search.py`
Search endpoints:
- POST /api/search/query - Hybrid search across all websets or specific one
- POST /api/search/semantic - Pure semantic search
- POST /api/search/lexical - Pure keyword search
- GET /api/search/suggest - Search suggestions/autocomplete

### 6. `analytics.py`
Analytics and stats:
- GET /api/analytics/dashboard - Dashboard stats
- GET /api/analytics/websets/{id}/insights - Webset insights
- GET /api/analytics/trending - Trending topics/entities
- GET /api/analytics/timeline - Activity timeline

### 7. `export.py`
Data export:
- GET /api/export/websets/{id}/json - Export as JSON
- GET /api/export/websets/{id}/csv - Export as CSV
- GET /api/export/websets/{id}/markdown - Export as Markdown

## Common Patterns
- Use dependency injection for db session: `db: AsyncSession = Depends(get_db_session)`
- Use Pydantic schemas for request/response validation
- Include error handling with HTTPException
- Add logging for all operations
- Return proper status codes (201 for create, 204 for delete, etc)
- Include pagination with query params (skip, limit)
- Add filtering and sorting support

## Integration
- Use WebsetManager, MonitorExecutor, EnrichmentEngine from respective modules
- Trigger Celery tasks for async operations (extraction, enrichment)
- Return task IDs for async operations with status endpoints
