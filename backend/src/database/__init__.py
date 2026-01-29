"""
Database package for the intelligence pipeline.

Exports SQLAlchemy models, connection management, and session utilities.
"""
from .connection import (
    DatabaseManager,
    get_db_manager,
    get_db_session,
    init_database,
)
from .models import (
    Base,
    ExtractionJob,
    Monitor,
    MonitorRun,
    Webset,
    WebsetItem,
)

__all__ = [
    # Models
    "Base",
    "Webset",
    "WebsetItem",
    "Monitor",
    "MonitorRun",
    "ExtractionJob",
    # Connection
    "DatabaseManager",
    "init_database",
    "get_db_manager",
    "get_db_session",
]
