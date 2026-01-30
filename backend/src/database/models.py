"""
SQLAlchemy models for the intelligence pipeline database.
"""
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class Webset(Base):
    """
    Webset table for managing collections of web content.

    A webset represents a curated collection of web pages/content
    with associated search criteria and entity type classification.
    """
    __tablename__ = "websets"

    id: str = Column(String, primary_key=True)
    name: str = Column(String, nullable=False)
    search_query: Optional[str] = Column(Text, nullable=True)
    search_criteria: Optional[Dict[str, Any]] = Column(JSON, nullable=True)
    entity_type: Optional[str] = Column(String, nullable=True)
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    items = relationship("WebsetItem", back_populates="webset", cascade="all, delete-orphan")
    monitors = relationship("Monitor", back_populates="webset", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Webset(id={self.id}, name={self.name})>"


class WebsetItem(Base):
    """
    WebsetItem table for individual items within a webset.

    Each item represents a single web page or piece of content
    with its metadata, enrichments, and link to the vector database.
    """
    __tablename__ = "webset_items"

    id: str = Column(String, primary_key=True)
    webset_id: str = Column(String, ForeignKey("websets.id", ondelete="CASCADE"), nullable=False)
    url: str = Column(Text, nullable=False)
    title: Optional[str] = Column(Text, nullable=True)
    content_hash: Optional[str] = Column(String, nullable=True)
    item_metadata: Optional[Dict[str, Any]] = Column(JSON, nullable=True)
    enrichments: Optional[Dict[str, Any]] = Column(JSON, nullable=True)
    milvus_doc_id: Optional[str] = Column(String, nullable=True)
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    webset = relationship("Webset", back_populates="items")

    def __repr__(self) -> str:
        return f"<WebsetItem(id={self.id}, url={self.url})>"


class Monitor(Base):
    """
    Monitor table for scheduled webset monitoring tasks.

    Monitors enable automatic updates to websets via cron-based scheduling
    with configurable behavior types (search, refresh, hybrid).
    """
    __tablename__ = "monitors"

    id: str = Column(String, primary_key=True)
    webset_id: str = Column(String, ForeignKey("websets.id", ondelete="CASCADE"), nullable=False)
    cron_expression: str = Column(String, nullable=False)
    timezone: str = Column(String, default="UTC", nullable=False)
    behavior_type: Optional[str] = Column(String, nullable=True)
    behavior_config: Optional[Dict[str, Any]] = Column(JSON, nullable=True)
    status: str = Column(String, default="enabled", nullable=False)
    last_run_at: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    webset = relationship("Webset", back_populates="monitors")
    runs = relationship("MonitorRun", back_populates="monitor", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Monitor(id={self.id}, webset_id={self.webset_id}, cron={self.cron_expression})>"


class MonitorRun(Base):
    """
    MonitorRun table for tracking individual monitor execution history.

    Each run records the status, results, and any errors from
    a monitor's execution.
    """
    __tablename__ = "monitor_runs"

    id: str = Column(String, primary_key=True)
    monitor_id: str = Column(String, ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False)
    status: Optional[str] = Column(String, nullable=True)
    items_added: Optional[int] = Column(Integer, nullable=True)
    items_updated: Optional[int] = Column(Integer, nullable=True)
    started_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    error_message: Optional[str] = Column(Text, nullable=True)

    # Relationships
    monitor = relationship("Monitor", back_populates="runs")

    def __repr__(self) -> str:
        return f"<MonitorRun(id={self.id}, monitor_id={self.monitor_id}, status={self.status})>"


class ExtractionJob(Base):
    """
    ExtractionJob table for tracking web extraction tasks.

    Jobs track the lifecycle of content extraction from URLs,
    including status, results, and error information.
    """
    __tablename__ = "extraction_jobs"

    id: str = Column(String, primary_key=True)
    url: str = Column(Text, nullable=False)
    status: Optional[str] = Column(String, nullable=True)
    result: Optional[Dict[str, Any]] = Column(JSON, nullable=True)
    error: Optional[str] = Column(Text, nullable=True)
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<ExtractionJob(id={self.id}, url={self.url}, status={self.status})>"
