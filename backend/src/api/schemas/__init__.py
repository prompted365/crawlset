"""
Pydantic schemas for API request/response validation.

Provides type-safe schemas for all database models and API operations.
"""
from .extraction import (
    ExtractionJobCreate,
    ExtractionJobResponse,
    ExtractionJobUpdate,
)
from .monitor import (
    MonitorCreate,
    MonitorResponse,
    MonitorRunCreate,
    MonitorRunResponse,
    MonitorUpdate,
)
from .webset import (
    WebsetCreate,
    WebsetItemCreate,
    WebsetItemResponse,
    WebsetResponse,
    WebsetUpdate,
)

__all__ = [
    # Webset schemas
    "WebsetCreate",
    "WebsetUpdate",
    "WebsetResponse",
    "WebsetItemCreate",
    "WebsetItemResponse",
    # Monitor schemas
    "MonitorCreate",
    "MonitorUpdate",
    "MonitorResponse",
    "MonitorRunCreate",
    "MonitorRunResponse",
    # Extraction schemas
    "ExtractionJobCreate",
    "ExtractionJobUpdate",
    "ExtractionJobResponse",
]
