"""
E2E Smoke Test with Cascading Unit Test Fallback.

Strategy:
  1. Smoke test hits the live FastAPI app via ASGI transport.
  2. If the smoke test fails (service down, DB not initialised, etc.),
     cascading unit tests fire to pinpoint exactly which layer broke:
       - Layer 0: Database engine + table creation
       - Layer 1: Model CRUD (Webset, WebsetItem, Monitor, MonitorRun)
       - Layer 2: Pydantic schema validation
       - Layer 3: API route handlers (via test client)
       - Layer 4: Full E2E flow (create webset → add items → monitor → search)

The cascade gives immediate visibility into the failure boundary.
"""
import pytest
import pytest_asyncio
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    Base,
    ExtractionJob,
    Monitor,
    MonitorRun,
    Webset,
    WebsetItem,
)
from src.api.schemas.webset import (
    WebsetCreate,
    WebsetItemCreate,
    WebsetResponse,
    WebsetItemResponse,
    WebsetUpdate,
)
from src.api.schemas.monitor import (
    MonitorCreate,
    MonitorUpdate,
    MonitorResponse,
    MonitorRunResponse,
)

from conftest import make_webset_id, make_monitor_id, make_item_id


# ============================================================================
# Smoke test (top-level)
# ============================================================================


class TestSmoke:
    """
    Fast smoke test against the live-ish app.
    If ANY of these fail, the cascade tests below will isolate the layer.
    """

    @pytest.mark.asyncio
    async def test_health_endpoint(self, app_client):
        resp = await app_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("healthy", "ok", "degraded")

    @pytest.mark.asyncio
    async def test_create_and_list_webset(self, app_client):
        payload = {
            "name": "Smoke Test Webset",
            "search_query": "smoke test query",
            "entity_type": "article",
        }
        resp = await app_client.post("/api/websets/", json=payload)
        assert resp.status_code == 201, f"Create failed: {resp.text}"

        created = resp.json()
        assert created["name"] == "Smoke Test Webset"

        # List should include the new webset
        resp = await app_client.get("/api/websets/")
        assert resp.status_code == 200
        websets = resp.json()
        assert any(w["id"] == created["id"] for w in websets)

    @pytest.mark.asyncio
    async def test_webset_get_and_delete(self, app_client):
        # Create
        resp = await app_client.post("/api/websets/", json={
            "name": "Delete Me",
            "entity_type": "test",
        })
        assert resp.status_code == 201
        ws_id = resp.json()["id"]

        # Get
        resp = await app_client.get(f"/api/websets/{ws_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Delete Me"

        # Delete
        resp = await app_client.delete(f"/api/websets/{ws_id}")
        assert resp.status_code == 204

        # Verify gone
        resp = await app_client.get(f"/api/websets/{ws_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_webset_update(self, app_client):
        resp = await app_client.post("/api/websets/", json={
            "name": "Before Update",
        })
        ws_id = resp.json()["id"]

        resp = await app_client.patch(f"/api/websets/{ws_id}", json={
            "name": "After Update",
            "entity_type": "updated",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "After Update"

    @pytest.mark.asyncio
    async def test_webset_stats(self, app_client):
        resp = await app_client.post("/api/websets/", json={
            "name": "Stats Test",
        })
        ws_id = resp.json()["id"]

        resp = await app_client.get(f"/api/websets/{ws_id}/stats")
        assert resp.status_code == 200
        stats = resp.json()
        assert stats["item_count"] == 0
        assert stats["enriched_count"] == 0

    @pytest.mark.asyncio
    async def test_nonexistent_webset_404(self, app_client):
        resp = await app_client.get("/api/websets/nonexistent-id-12345")
        assert resp.status_code == 404


# ============================================================================
# CASCADE LAYER 0 – Database Engine + Schema
# ============================================================================


class TestCascadeLayer0_Database:
    """Verify the database engine works and tables exist."""

    @pytest.mark.asyncio
    async def test_engine_connects(self, db_engine):
        async with db_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_tables_created(self, db_engine):
        async with db_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            )
            tables = {row[0] for row in result.fetchall()}

        expected = {"websets", "webset_items", "monitors", "monitor_runs", "extraction_jobs"}
        assert expected.issubset(tables), f"Missing tables: {expected - tables}"


# ============================================================================
# CASCADE LAYER 1 – Model CRUD
# ============================================================================


class TestCascadeLayer1_Models:
    """Direct ORM model operations without the API layer."""

    @pytest.mark.asyncio
    async def test_webset_create_read(self, db_session: AsyncSession):
        ws = Webset(
            id=make_webset_id(),
            name="Layer1 Webset",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(ws)
        await db_session.commit()

        result = await db_session.execute(select(Webset).where(Webset.id == ws.id))
        assert result.scalar_one().name == "Layer1 Webset"

    @pytest.mark.asyncio
    async def test_webset_item_create_read(self, db_session: AsyncSession):
        ws = Webset(
            id=make_webset_id(),
            name="Layer1 Items",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(ws)
        await db_session.flush()

        item = WebsetItem(
            id=make_item_id(),
            webset_id=ws.id,
            url="https://example.com",
            title="Example",
        )
        db_session.add(item)
        await db_session.commit()

        result = await db_session.execute(
            select(WebsetItem).where(WebsetItem.webset_id == ws.id)
        )
        assert result.scalar_one().url == "https://example.com"

    @pytest.mark.asyncio
    async def test_monitor_create_read(self, db_session: AsyncSession):
        ws = Webset(
            id=make_webset_id(),
            name="Layer1 Monitor",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(ws)
        await db_session.flush()

        mon = Monitor(
            id=make_monitor_id(),
            webset_id=ws.id,
            cron_expression="0 9 * * *",
            timezone="UTC",
            status="enabled",
        )
        db_session.add(mon)
        await db_session.commit()

        result = await db_session.execute(select(Monitor).where(Monitor.id == mon.id))
        assert result.scalar_one().cron_expression == "0 9 * * *"

    @pytest.mark.asyncio
    async def test_monitor_run_create_read(self, db_session: AsyncSession):
        ws = Webset(
            id=make_webset_id(), name="Layer1 Run",
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )
        db_session.add(ws)
        await db_session.flush()

        mon = Monitor(
            id=make_monitor_id(), webset_id=ws.id,
            cron_expression="0 0 * * *", timezone="UTC", status="enabled",
        )
        db_session.add(mon)
        await db_session.flush()

        run = MonitorRun(
            id=f"run-{uuid4().hex[:12]}",
            monitor_id=mon.id,
            status="completed",
            items_added=3,
            started_at=datetime.utcnow(),
        )
        db_session.add(run)
        await db_session.commit()

        result = await db_session.execute(
            select(MonitorRun).where(MonitorRun.monitor_id == mon.id)
        )
        assert result.scalar_one().items_added == 3

    @pytest.mark.asyncio
    async def test_extraction_job_create_read(self, db_session: AsyncSession):
        job = ExtractionJob(
            id=f"job-{uuid4().hex[:12]}",
            url="https://example.com/extract",
            status="pending",
            created_at=datetime.utcnow(),
        )
        db_session.add(job)
        await db_session.commit()

        result = await db_session.execute(
            select(ExtractionJob).where(ExtractionJob.id == job.id)
        )
        assert result.scalar_one().status == "pending"

    @pytest.mark.asyncio
    async def test_cascade_delete_webset_items(self, db_session: AsyncSession):
        ws = Webset(
            id=make_webset_id(), name="Cascade Test",
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )
        db_session.add(ws)
        await db_session.flush()

        for i in range(5):
            db_session.add(WebsetItem(
                id=make_item_id(), webset_id=ws.id,
                url=f"https://example.com/{i}",
            ))
        await db_session.commit()

        await db_session.delete(ws)
        await db_session.commit()

        result = await db_session.execute(
            select(WebsetItem).where(WebsetItem.webset_id == ws.id)
        )
        assert len(result.scalars().all()) == 0


# ============================================================================
# CASCADE LAYER 2 – Pydantic Schema Validation
# ============================================================================


class TestCascadeLayer2_Schemas:
    """Pydantic models validate and serialise correctly."""

    def test_webset_create_valid(self):
        ws = WebsetCreate(
            name="Valid Webset",
            search_query="test",
            entity_type="article",
        )
        assert ws.name == "Valid Webset"
        assert ws.id is None  # auto-generated

    def test_webset_create_with_id(self):
        ws = WebsetCreate(id="custom-id", name="Custom")
        assert ws.id == "custom-id"

    def test_webset_create_requires_name(self):
        with pytest.raises(Exception):
            WebsetCreate()  # name is required

    def test_webset_update_all_optional(self):
        update = WebsetUpdate()
        dumped = update.model_dump(exclude_unset=True)
        assert dumped == {}

    def test_webset_response_from_attributes(self):
        resp = WebsetResponse(
            id="test",
            name="Test",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        assert resp.id == "test"

    def test_monitor_create_valid(self):
        mon = MonitorCreate(
            id="mon-test",
            webset_id="ws-test",
            cron_expression="0 */6 * * *",
        )
        assert mon.timezone == "UTC"
        assert mon.status == "enabled"

    def test_monitor_update_partial(self):
        update = MonitorUpdate(status="disabled")
        dumped = update.model_dump(exclude_unset=True)
        assert dumped == {"status": "disabled"}

    def test_webset_item_create_valid(self):
        item = WebsetItemCreate(
            webset_id="ws-test",
            url="https://example.com",
        )
        assert item.ruvector_doc_id is None

    def test_monitor_response_from_attributes(self):
        resp = MonitorResponse(
            id="mon-1",
            webset_id="ws-1",
            cron_expression="0 0 * * *",
            timezone="UTC",
            status="enabled",
        )
        assert resp.last_run_at is None


# ============================================================================
# CASCADE LAYER 3 – API Route Handlers (via test client)
# ============================================================================


class TestCascadeLayer3_Routes:
    """API routes via ASGI test client."""

    @pytest.mark.asyncio
    async def test_list_websets_empty(self, app_client):
        resp = await app_client.get("/api/websets/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_create_webset_minimal(self, app_client):
        resp = await app_client.post("/api/websets/", json={"name": "Minimal"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Minimal"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_webset_full_payload(self, app_client):
        resp = await app_client.post("/api/websets/", json={
            "name": "Full Payload",
            "search_query": "agentic perception research",
            "entity_type": "research_paper",
            "search_criteria": {"domains": ["perception", "agents"]},
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["entity_type"] == "research_paper"

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_404(self, app_client):
        resp = await app_client.get("/api/websets/no-such-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_404(self, app_client):
        resp = await app_client.delete("/api/websets/no-such-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_patch_nonexistent_returns_404(self, app_client):
        resp = await app_client.patch("/api/websets/no-such-id", json={"name": "X"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_items_nonexistent_webset_404(self, app_client):
        resp = await app_client.get("/api/websets/no-such-id/items")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_stats_nonexistent_webset_404(self, app_client):
        resp = await app_client.get("/api/websets/no-such-id/stats")
        assert resp.status_code == 404


# ============================================================================
# CASCADE LAYER 4 – Full E2E Flow
# ============================================================================


class TestCascadeLayer4_E2E:
    """
    Complete end-to-end: create research websets → add items → verify stats.
    """

    @pytest.mark.asyncio
    async def test_e2e_perception_webset_lifecycle(self, app_client):
        # 1. Create webset
        resp = await app_client.post("/api/websets/", json={
            "name": "E2E Perception Webset",
            "search_query": "perception agentic orchestration systems",
            "entity_type": "research_paper",
        })
        assert resp.status_code == 201
        ws_id = resp.json()["id"]

        # 2. Verify it exists
        resp = await app_client.get(f"/api/websets/{ws_id}")
        assert resp.status_code == 200
        assert resp.json()["search_query"] == "perception agentic orchestration systems"

        # 3. Check stats (empty)
        resp = await app_client.get(f"/api/websets/{ws_id}/stats")
        assert resp.status_code == 200
        assert resp.json()["item_count"] == 0

        # 4. Update name
        resp = await app_client.patch(f"/api/websets/{ws_id}", json={
            "name": "Perception in Agentic Orchestration – Updated",
        })
        assert resp.status_code == 200
        assert "Updated" in resp.json()["name"]

        # 5. List includes our webset
        resp = await app_client.get("/api/websets/", params={"entity_type": "research_paper"})
        assert resp.status_code == 200
        ids = [w["id"] for w in resp.json()]
        assert ws_id in ids

        # 6. Delete
        resp = await app_client.delete(f"/api/websets/{ws_id}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_e2e_bio_webset_lifecycle(self, app_client):
        # Create
        resp = await app_client.post("/api/websets/", json={
            "name": "E2E Bio-Inspired Agentic Design",
            "search_query": "biologically inspired constrained agentic design systems",
            "entity_type": "research_paper",
            "search_criteria": {
                "keywords": ["neuromorphic", "stigmergy", "homeostasis", "morphogenesis"],
            },
        })
        assert resp.status_code == 201
        ws_id = resp.json()["id"]

        # Read back
        resp = await app_client.get(f"/api/websets/{ws_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "biologically inspired" in data["search_query"]

        # Filter by entity type
        resp = await app_client.get("/api/websets/", params={"entity_type": "research_paper"})
        assert resp.status_code == 200
        assert any(w["id"] == ws_id for w in resp.json())

        # Cleanup
        resp = await app_client.delete(f"/api/websets/{ws_id}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_e2e_monitor_create_for_webset(self, app_client):
        # Create webset
        resp = await app_client.post("/api/websets/", json={
            "name": "Monitored Research Webset",
            "search_query": "agent perception",
            "entity_type": "research_paper",
        })
        ws_id = resp.json()["id"]

        # Create monitor
        resp = await app_client.post("/api/monitors/", json={
            "id": make_monitor_id(),
            "webset_id": ws_id,
            "cron_expression": "0 0 31 2 *",
            "timezone": "UTC",
            "behavior_type": "search",
            "behavior_config": {"max_results": 50},
            "status": "enabled",
        })
        assert resp.status_code == 201
        mon_id = resp.json()["id"]

        # Verify monitor
        resp = await app_client.get(f"/api/monitors/{mon_id}")
        assert resp.status_code == 200
        assert resp.json()["webset_id"] == ws_id

        # List monitors
        resp = await app_client.get("/api/monitors/", params={"webset_id": ws_id})
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

        # Delete monitor
        resp = await app_client.delete(f"/api/monitors/{mon_id}")
        assert resp.status_code == 204

        # Cleanup webset
        resp = await app_client.delete(f"/api/websets/{ws_id}")
        assert resp.status_code == 204
