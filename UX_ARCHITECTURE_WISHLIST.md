# UX / Architecture Improvements Wishlist

Observations collected during the RuVector migration and E2E test authoring. Items are ordered by severity: bugs first, then friction points, then enhancements.

---

## Bugs (Fix Before Ship)

### BUG-1: `astradb_doc_id` reference in webset item creation route
- **File**: `backend/src/api/routes/websets.py:374`
- **Issue**: The `add_webset_item` handler sets `astradb_doc_id=item.astradb_doc_id` but:
  - The Pydantic schema (`WebsetItemCreate`) defines `ruvector_doc_id`
  - The SQLAlchemy model (`WebsetItem`) defines `ruvector_doc_id`
  - There is no `astradb_doc_id` on either the schema or the model
- **Impact**: Creating a webset item via the API will fail with an `AttributeError` on the schema or silently drop the vector doc ID.
- **Fix**: Change line 374 to `ruvector_doc_id=item.ruvector_doc_id`.

### BUG-2: `item_metadata` vs `metadata` field name mismatch
- **File**: `backend/src/database/models.py:55` vs `backend/src/api/routes/websets.py:373`
- **Issue**: The SQLAlchemy column is named `item_metadata` but the route passes `metadata=item.metadata`. The Pydantic schema uses `metadata`.
- **Impact**: Inserting items via the API stores metadata under the wrong column name (or silently drops it), and querying items back returns `metadata: null` while the data sits in `item_metadata`.
- **Fix**: Either:
  - (a) Rename the model column to `metadata` (breaking if there's existing data), or
  - (b) Add `Column("metadata", JSON, ...)` with `key="item_metadata"` for the mapping, or
  - (c) Align the route to use `item_metadata=item.metadata`.
- **Recommendation**: Option (c) is safest — update the route and add a Pydantic alias on `WebsetItemResponse` to map `item_metadata` → `metadata` for the API contract.

### BUG-3: `WebsetItemCreate.id` has no auto-generation
- **File**: `backend/src/api/schemas/webset.py:42`, `backend/src/api/routes/websets.py:367`
- **Issue**: `WebsetItemCreate.id` is `Optional[str]` with no default factory. If a client omits `id`, it inserts `None` as the primary key, which will violate the NOT NULL constraint.
- **Fix**: Add `default_factory=lambda: str(uuid4())` or auto-generate in the route (like `WebsetCreate` does for websets).

---

## Friction Points (Developer Experience)

### FRICTION-1: No pytest conftest.py or test fixtures
- **Before**: The repo had a single `test_milvus.py` that required a running RuVector service. No shared fixtures, no in-memory DB, no test client.
- **Status**: Fixed in this PR — `conftest.py` now provides `db_session`, `app_client`, and factory helpers.

### FRICTION-2: Monitor `id` is required on create
- **File**: `backend/src/api/schemas/monitor.py:12`
- **Issue**: `MonitorCreate.id` is `str = Field(...)` (required). Every other entity auto-generates IDs. Clients must supply UUIDs themselves.
- **Recommendation**: Change to `Optional[str]` with auto-generation in the route handler (matching the webset pattern).

### FRICTION-3: No pagination metadata in list responses
- **Files**: All list endpoints (`GET /api/websets/`, `GET /api/monitors/`, etc.)
- **Issue**: Responses are bare arrays with no `total_count`, `has_more`, or `next_offset`. Frontend must guess when to stop paginating.
- **Recommendation**: Return `{"items": [...], "total": N, "skip": X, "limit": Y}` wrapper.

### FRICTION-4: `WebsetItemResponse` inherits `from_attributes=True` but model uses `item_metadata`
- The Pydantic response model expects a `metadata` field, but SQLAlchemy exposes `item_metadata`. `from_attributes=True` won't auto-map misnamed fields.
- Related to BUG-2.

### FRICTION-5: MonitorExecutor instantiated per request
- **File**: `backend/src/api/routes/websets.py:42-46`, `backend/src/api/routes/monitors.py:34-39`
- **Issue**: `get_monitor_executor()` creates a new `MonitorExecutor` (and implicitly a new DB engine) on every request. This defeats connection pooling and is wasteful.
- **Recommendation**: Initialise once on app startup via `lifespan()` and store on `app.state`.

### FRICTION-6: Settings loaded at module import time
- **File**: `backend/src/api/routes/websets.py:33`, `backend/src/api/routes/monitors.py:31`
- **Issue**: `settings = get_settings()` runs at import time, not at request time. This makes it hard to override settings in tests and can cause import-order issues.
- **Recommendation**: Use `Depends(get_settings)` or access `app.state.settings` in route handlers.

---

## Architecture Improvements

### ARCH-1: WebsetManager has its own engine, bypassing FastAPI DI
- **File**: `backend/src/websets/manager.py`
- **Issue**: `WebsetManager.__init__` creates its own SQLAlchemy engine from `db_url`. Routes also inject `db: AsyncSession` via `Depends(get_db_session)`. This means there are two separate database connections per request.
- **Recommendation**: Refactor `WebsetManager` to accept an `AsyncSession` instead of a `db_url`, matching the DI pattern already used in the route handlers.

### ARCH-2: No API authentication or rate limiting
- All endpoints are wide open. For a self-hosted tool this is acceptable initially, but should be addressed before any multi-user or cloud deployment.
- **Recommendation**: Add optional API key middleware (configurable via `.env`).

### ARCH-3: SearchExecutor fallback creates un-initialised RuVectorClient
- **File**: `backend/src/websets/search.py:51`
- **Issue**: If no `ruvector_client` is injected, it creates a bare `RuVectorClient()` but never calls `initialize()`. The first HTTP call will fail because the httpx client isn't set up.
- **Recommendation**: Either call `await client.initialize()` in the fallback or make `RuVectorClient` lazy-init on first request.

### ARCH-4: No retry/circuit-breaker for RuVector HTTP calls
- If the RuVector Rust service is temporarily down, every API request that touches search will fail hard.
- **Recommendation**: Add `tenacity` retry with exponential backoff, or a circuit breaker that degrades gracefully (return empty results + warning).

### ARCH-5: Export routes have no streaming for large websets
- **File**: `backend/src/api/routes/export.py`
- **Issue**: JSON/CSV/Markdown exports load all items into memory. For websets with thousands of items this will OOM.
- **Recommendation**: Use `StreamingResponse` with an async generator that yields rows.

---

## Frontend UX Improvements

### UX-1: No loading states for search/extraction
- Extraction jobs are async (returns `job_id`), but there's no polling or WebSocket notification for completion. The user has to manually refresh.
- **Recommendation**: Add polling with exponential backoff or SSE/WebSocket push.

### UX-2: No error toast / notification system
- API errors are silently swallowed or shown as raw JSON. Need a toast notification system.

### UX-3: Monitor cron expression is raw text
- Users must manually type cron expressions like `0 */6 * * *`. A visual cron builder or preset selector would reduce errors.

### UX-4: No bulk operations UI
- Websets, items, and monitors can only be managed one at a time. Bulk select, bulk delete, bulk enrich would be valuable.

### UX-5: No diff view for monitor runs
- When a monitor adds or updates items, there's no way to see what changed. A before/after diff view for content updates would help.

---

## Performance

### PERF-1: N+1 query in list endpoints
- List endpoints fetch the collection, then each response model may trigger lazy loads for relationships.
- **Recommendation**: Use `selectinload()` or `joinedload()` for relationships needed in responses.

### PERF-2: No index on `webset_items.webset_id`
- Listing items by webset_id does a full table scan if the foreign key isn't indexed.
- **Recommendation**: Add `Index("ix_webset_items_webset_id", WebsetItem.webset_id)`.

### PERF-3: BM25 index rebuilt per search
- `HybridSearchEngine` appears to rebuild the BM25 index on every search call rather than maintaining a persistent index.
- **Recommendation**: Build BM25 index once on startup and incrementally update on insert/delete.

---

## Testing Gaps

### TEST-1: No integration tests for Celery tasks
- Tasks like `extract_url_task`, `batch_extract_task`, `run_monitor_task` are untested.
- **Recommendation**: Add tests with Celery's `task_always_eager` setting.

### TEST-2: No tests for export endpoints
- JSON, CSV, Markdown export routes are completely untested.

### TEST-3: No tests for enrichment pipeline
- The enrichment plugin system (`BaseEnricher`, `EnrichmentEngine`) has no test coverage.

### TEST-4: No load tests
- No k6/locust scripts for verifying performance under concurrent load.

---

*This document should be revisited after the system is confirmed live. Items are independent and can be tackled in any order.*
