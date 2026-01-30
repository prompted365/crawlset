"""
Webset CRUD operations with SQLAlchemy for managing websets and their items.
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import hashlib
import json
import uuid

from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.future import select
from sqlalchemy import update, delete

Base = declarative_base()


class Webset(Base):
    __tablename__ = "websets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    search_query = Column(Text, nullable=True)
    search_criteria = Column(Text, nullable=True)  # JSON
    entity_type = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("WebsetItem", back_populates="webset", cascade="all, delete-orphan")
    monitors = relationship("Monitor", back_populates="webset", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "search_query": self.search_query,
            "search_criteria": json.loads(self.search_criteria) if self.search_criteria else None,
            "entity_type": self.entity_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class WebsetItem(Base):
    __tablename__ = "webset_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    webset_id = Column(String, ForeignKey("websets.id"), nullable=False)
    url = Column(String, nullable=False)
    title = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    content_hash = Column(String, nullable=True)
    item_metadata = Column(Text, nullable=True)  # JSON
    enrichments = Column(Text, nullable=True)  # JSON
    milvus_doc_id = Column(String, nullable=True)
    last_crawled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    webset = relationship("Webset", back_populates="items")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "webset_id": self.webset_id,
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "content_hash": self.content_hash,
            "metadata": json.loads(self.item_metadata) if self.item_metadata else None,
            "enrichments": json.loads(self.enrichments) if self.enrichments else None,
            "milvus_doc_id": self.milvus_doc_id,
            "last_crawled_at": self.last_crawled_at.isoformat() if self.last_crawled_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Monitor(Base):
    __tablename__ = "monitors"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    webset_id = Column(String, ForeignKey("websets.id"), nullable=False)
    cron_expression = Column(String, nullable=False)
    timezone = Column(String, default="UTC")
    behavior_type = Column(String, nullable=False)  # search, refresh, hybrid
    behavior_config = Column(Text, nullable=True)  # JSON
    status = Column(String, default="enabled")  # enabled, disabled, error
    last_run_at = Column(DateTime, nullable=True)

    webset = relationship("Webset", back_populates="monitors")
    runs = relationship("MonitorRun", back_populates="monitor", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "webset_id": self.webset_id,
            "cron_expression": self.cron_expression,
            "timezone": self.timezone,
            "behavior_type": self.behavior_type,
            "behavior_config": json.loads(self.behavior_config) if self.behavior_config else None,
            "status": self.status,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
        }


class MonitorRun(Base):
    __tablename__ = "monitor_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    monitor_id = Column(String, ForeignKey("monitors.id"), nullable=False)
    status = Column(String, nullable=False)  # running, completed, failed
    items_added = Column(Integer, default=0)
    items_updated = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    monitor = relationship("Monitor", back_populates="runs")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "monitor_id": self.monitor_id,
            "status": self.status,
            "items_added": self.items_added,
            "items_updated": self.items_updated,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }


class WebsetManager:
    """Async-first manager for webset CRUD operations."""

    def __init__(self, db_url: str = "sqlite+aiosqlite:///./data/websets.db"):
        self.db_url = db_url
        self.engine = create_async_engine(db_url, echo=False)
        self.async_session = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def init_db(self):
        """Initialize database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def create_webset(
        self,
        name: str,
        search_query: Optional[str] = None,
        search_criteria: Optional[Dict[str, Any]] = None,
        entity_type: Optional[str] = None,
    ) -> Webset:
        """Create a new webset."""
        async with self.async_session() as session:
            webset = Webset(
                name=name,
                search_query=search_query,
                search_criteria=json.dumps(search_criteria) if search_criteria else None,
                entity_type=entity_type,
            )
            session.add(webset)
            await session.commit()
            await session.refresh(webset)
            return webset

    async def get_webset(self, webset_id: str) -> Optional[Webset]:
        """Get a webset by ID."""
        async with self.async_session() as session:
            result = await session.execute(
                select(Webset).where(Webset.id == webset_id)
            )
            return result.scalars().first()

    async def list_websets(self, limit: int = 100, offset: int = 0) -> List[Webset]:
        """List all websets."""
        async with self.async_session() as session:
            result = await session.execute(
                select(Webset).order_by(Webset.updated_at.desc()).limit(limit).offset(offset)
            )
            return list(result.scalars().all())

    async def update_webset(
        self,
        webset_id: str,
        name: Optional[str] = None,
        search_query: Optional[str] = None,
        search_criteria: Optional[Dict[str, Any]] = None,
        entity_type: Optional[str] = None,
    ) -> Optional[Webset]:
        """Update a webset."""
        async with self.async_session() as session:
            result = await session.execute(
                select(Webset).where(Webset.id == webset_id)
            )
            webset = result.scalars().first()
            if not webset:
                return None

            if name is not None:
                webset.name = name
            if search_query is not None:
                webset.search_query = search_query
            if search_criteria is not None:
                webset.search_criteria = json.dumps(search_criteria)
            if entity_type is not None:
                webset.entity_type = entity_type

            webset.updated_at = datetime.utcnow()
            await session.commit()
            await session.refresh(webset)
            return webset

    async def delete_webset(self, webset_id: str) -> bool:
        """Delete a webset and all its items."""
        async with self.async_session() as session:
            result = await session.execute(
                delete(Webset).where(Webset.id == webset_id)
            )
            await session.commit()
            return result.rowcount > 0

    # WebsetItem operations

    async def add_item(
        self,
        webset_id: str,
        url: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[WebsetItem]:
        """Add an item to a webset."""
        async with self.async_session() as session:
            # Check if webset exists
            result = await session.execute(
                select(Webset).where(Webset.id == webset_id)
            )
            if not result.scalars().first():
                return None

            # Calculate content hash if content provided
            content_hash = None
            if content:
                content_hash = hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()

            item = WebsetItem(
                webset_id=webset_id,
                url=url,
                title=title,
                content=content,
                content_hash=content_hash,
                metadata=json.dumps(metadata) if metadata else None,
            )
            session.add(item)
            await session.commit()
            await session.refresh(item)
            return item

    async def get_item(self, item_id: str) -> Optional[WebsetItem]:
        """Get a webset item by ID."""
        async with self.async_session() as session:
            result = await session.execute(
                select(WebsetItem).where(WebsetItem.id == item_id)
            )
            return result.scalars().first()

    async def get_items(
        self, webset_id: str, limit: int = 100, offset: int = 0
    ) -> List[WebsetItem]:
        """Get all items in a webset."""
        async with self.async_session() as session:
            result = await session.execute(
                select(WebsetItem)
                .where(WebsetItem.webset_id == webset_id)
                .order_by(WebsetItem.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            return list(result.scalars().all())

    async def update_item(
        self,
        item_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        enrichments: Optional[Dict[str, Any]] = None,
        ruvector_doc_id: Optional[str] = None,
    ) -> Optional[WebsetItem]:
        """Update a webset item."""
        async with self.async_session() as session:
            result = await session.execute(
                select(WebsetItem).where(WebsetItem.id == item_id)
            )
            item = result.scalars().first()
            if not item:
                return None

            if title is not None:
                item.title = title
            if content is not None:
                item.content = content
                item.content_hash = hashlib.sha256(
                    content.encode("utf-8", errors="ignore")
                ).hexdigest()
                item.last_crawled_at = datetime.utcnow()
            if metadata is not None:
                item.metadata = json.dumps(metadata)
            if enrichments is not None:
                item.enrichments = json.dumps(enrichments)
            if ruvector_doc_id is not None:
                item.ruvector_doc_id = ruvector_doc_id

            await session.commit()
            await session.refresh(item)
            return item

    async def delete_item(self, item_id: str) -> bool:
        """Delete a webset item."""
        async with self.async_session() as session:
            result = await session.execute(
                delete(WebsetItem).where(WebsetItem.id == item_id)
            )
            await session.commit()
            return result.rowcount > 0

    async def find_item_by_url(self, webset_id: str, url: str) -> Optional[WebsetItem]:
        """Find an item by URL in a webset."""
        async with self.async_session() as session:
            result = await session.execute(
                select(WebsetItem).where(
                    WebsetItem.webset_id == webset_id,
                    WebsetItem.url == url
                )
            )
            return result.scalars().first()

    async def find_item_by_content_hash(
        self, webset_id: str, content_hash: str
    ) -> Optional[WebsetItem]:
        """Find an item by content hash in a webset."""
        async with self.async_session() as session:
            result = await session.execute(
                select(WebsetItem).where(
                    WebsetItem.webset_id == webset_id,
                    WebsetItem.content_hash == content_hash
                )
            )
            return result.scalars().first()

    # Monitor operations

    async def create_monitor(
        self,
        webset_id: str,
        cron_expression: str,
        behavior_type: str,
        behavior_config: Optional[Dict[str, Any]] = None,
        timezone: str = "UTC",
    ) -> Optional[Monitor]:
        """Create a monitor for a webset."""
        async with self.async_session() as session:
            # Check if webset exists
            result = await session.execute(
                select(Webset).where(Webset.id == webset_id)
            )
            if not result.scalars().first():
                return None

            monitor = Monitor(
                webset_id=webset_id,
                cron_expression=cron_expression,
                timezone=timezone,
                behavior_type=behavior_type,
                behavior_config=json.dumps(behavior_config) if behavior_config else None,
            )
            session.add(monitor)
            await session.commit()
            await session.refresh(monitor)
            return monitor

    async def get_monitor(self, monitor_id: str) -> Optional[Monitor]:
        """Get a monitor by ID."""
        async with self.async_session() as session:
            result = await session.execute(
                select(Monitor).where(Monitor.id == monitor_id)
            )
            return result.scalars().first()

    async def list_monitors(
        self, webset_id: Optional[str] = None, status: Optional[str] = None
    ) -> List[Monitor]:
        """List monitors, optionally filtered by webset and status."""
        async with self.async_session() as session:
            query = select(Monitor)
            if webset_id:
                query = query.where(Monitor.webset_id == webset_id)
            if status:
                query = query.where(Monitor.status == status)
            result = await session.execute(query)
            return list(result.scalars().all())

    async def update_monitor(
        self,
        monitor_id: str,
        cron_expression: Optional[str] = None,
        behavior_type: Optional[str] = None,
        behavior_config: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        timezone: Optional[str] = None,
    ) -> Optional[Monitor]:
        """Update a monitor."""
        async with self.async_session() as session:
            result = await session.execute(
                select(Monitor).where(Monitor.id == monitor_id)
            )
            monitor = result.scalars().first()
            if not monitor:
                return None

            if cron_expression is not None:
                monitor.cron_expression = cron_expression
            if behavior_type is not None:
                monitor.behavior_type = behavior_type
            if behavior_config is not None:
                monitor.behavior_config = json.dumps(behavior_config)
            if status is not None:
                monitor.status = status
            if timezone is not None:
                monitor.timezone = timezone

            await session.commit()
            await session.refresh(monitor)
            return monitor

    async def delete_monitor(self, monitor_id: str) -> bool:
        """Delete a monitor."""
        async with self.async_session() as session:
            result = await session.execute(
                delete(Monitor).where(Monitor.id == monitor_id)
            )
            await session.commit()
            return result.rowcount > 0

    async def record_monitor_run(
        self,
        monitor_id: str,
        status: str,
        items_added: int = 0,
        items_updated: int = 0,
        error_message: Optional[str] = None,
    ) -> MonitorRun:
        """Record a monitor run."""
        async with self.async_session() as session:
            run = MonitorRun(
                monitor_id=monitor_id,
                status=status,
                items_added=items_added,
                items_updated=items_updated,
                completed_at=datetime.utcnow() if status in ["completed", "failed"] else None,
                error_message=error_message,
            )
            session.add(run)

            # Update monitor's last_run_at
            await session.execute(
                update(Monitor)
                .where(Monitor.id == monitor_id)
                .values(last_run_at=datetime.utcnow())
            )

            await session.commit()
            await session.refresh(run)
            return run

    async def get_monitor_runs(
        self, monitor_id: str, limit: int = 50
    ) -> List[MonitorRun]:
        """Get recent runs for a monitor."""
        async with self.async_session() as session:
            result = await session.execute(
                select(MonitorRun)
                .where(MonitorRun.monitor_id == monitor_id)
                .order_by(MonitorRun.started_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())
