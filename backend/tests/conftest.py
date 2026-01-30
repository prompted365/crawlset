"""
Shared test fixtures for the Crawlset intelligence pipeline.

Provides async database sessions, FastAPI test client, and
reusable test data factories for websets, monitors, and items.
"""
import asyncio
import os
from datetime import datetime
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.database.models import Base, ExtractionJob, Monitor, MonitorRun, Webset, WebsetItem

# Optional: full-stack deps for app_client (playwright, celery, etc.)
try:
    from httpx import ASGITransport, AsyncClient

    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

_FULL_STACK_AVAILABLE = False
try:
    from src.api.main import app as _fastapi_app  # noqa: F401

    _FULL_STACK_AVAILABLE = True
except ImportError:
    _fastapi_app = None

requires_full_stack = pytest.mark.skipif(
    not _FULL_STACK_AVAILABLE or not _HAS_HTTPX,
    reason="Full stack deps not installed (playwright, celery, etc.)",
)


# ---------------------------------------------------------------------------
# Event loop
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite:///./data/test_websets.db"


@pytest_asyncio.fixture
async def db_engine():
    """Create a fresh async engine per test pointing at a test database."""
    engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool, future=True)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Teardown – drop all tables so tests are isolated
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session for each test."""
    factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
    )
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def app_client(db_engine):
    """
    FastAPI AsyncClient wired to the test database.

    Patches the global database manager so route handlers use the test DB.
    Skips if full-stack deps (playwright, celery, etc.) are not available.
    """
    if not _FULL_STACK_AVAILABLE or not _HAS_HTTPX:
        pytest.skip("Full stack deps not installed (playwright, celery, etc.)")

    from src.database.connection import DatabaseManager
    from src.api.main import app

    # Swap the global DB manager to point at our test engine
    manager = DatabaseManager(TEST_DB_URL)
    manager._engine = db_engine
    manager._session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )

    import src.database.connection as conn_mod

    original = conn_mod._db_manager
    conn_mod._db_manager = manager

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    conn_mod._db_manager = original


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def make_webset_id() -> str:
    return f"ws-{uuid4().hex[:12]}"


def make_monitor_id() -> str:
    return f"mon-{uuid4().hex[:12]}"


def make_item_id() -> str:
    return f"item-{uuid4().hex[:12]}"


@pytest_asyncio.fixture
async def sample_webset(db_session: AsyncSession) -> Webset:
    """Insert a sample webset and return it."""
    ws = Webset(
        id=make_webset_id(),
        name="Test Webset",
        search_query="test query",
        entity_type="article",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


@pytest_asyncio.fixture
async def sample_webset_with_items(db_session: AsyncSession) -> Webset:
    """Insert a webset with 3 sample items."""
    ws = Webset(
        id=make_webset_id(),
        name="Populated Webset",
        search_query="populated test",
        entity_type="research",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(ws)
    await db_session.flush()

    for i in range(3):
        item = WebsetItem(
            id=make_item_id(),
            webset_id=ws.id,
            url=f"https://example.com/page-{i}",
            title=f"Page {i}",
            content_hash=f"hash_{i}",
            item_metadata={"index": i},
        )
        db_session.add(item)

    await db_session.commit()
    await db_session.refresh(ws)
    return ws


@pytest_asyncio.fixture
async def sample_monitor(db_session: AsyncSession, sample_webset: Webset) -> Monitor:
    """Insert a sample monitor linked to sample_webset."""
    mon = Monitor(
        id=make_monitor_id(),
        webset_id=sample_webset.id,
        cron_expression="0 */6 * * *",
        timezone="UTC",
        behavior_type="search",
        behavior_config={"max_results": 10},
        status="enabled",
    )
    db_session.add(mon)
    await db_session.commit()
    await db_session.refresh(mon)
    return mon
