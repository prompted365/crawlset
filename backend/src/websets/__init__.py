"""Webset management module."""
# search is NOT re-exported here — search.py has a top-level browser import.
# Import sub-modules directly: from ..websets.search import SearchExecutor
from .manager import WebsetManager, Webset, WebsetItem, Monitor, MonitorRun
from .deduplication import ContentDeduplicator, URLDeduplicator

__all__ = [
    "WebsetManager",
    "Webset",
    "WebsetItem",
    "Monitor",
    "MonitorRun",
    "ContentDeduplicator",
    "URLDeduplicator",
]
