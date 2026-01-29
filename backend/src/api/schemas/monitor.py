"""
Pydantic schemas for Monitor and MonitorRun models.
"""
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class MonitorCreate(BaseModel):
    """Schema for creating a new monitor."""
    id: str = Field(..., description="Unique identifier for the monitor")
    webset_id: str = Field(..., description="ID of the webset to monitor")
    cron_expression: str = Field(..., description="Cron expression for scheduling (e.g., '0 */6 * * *')")
    timezone: str = Field(default="UTC", description="Timezone for cron scheduling")
    behavior_type: Optional[str] = Field(None, description="Monitor behavior: 'search', 'refresh', or 'hybrid'")
    behavior_config: Optional[Dict[str, Any]] = Field(None, description="Configuration for the monitor behavior")
    status: str = Field(default="enabled", description="Monitor status: 'enabled' or 'disabled'")


class MonitorUpdate(BaseModel):
    """Schema for updating an existing monitor."""
    cron_expression: Optional[str] = Field(None, description="Cron expression for scheduling")
    timezone: Optional[str] = Field(None, description="Timezone for cron scheduling")
    behavior_type: Optional[str] = Field(None, description="Monitor behavior type")
    behavior_config: Optional[Dict[str, Any]] = Field(None, description="Configuration for the monitor behavior")
    status: Optional[str] = Field(None, description="Monitor status: 'enabled' or 'disabled'")


class MonitorResponse(BaseModel):
    """Schema for monitor responses."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    webset_id: str
    cron_expression: str
    timezone: str
    behavior_type: Optional[str] = None
    behavior_config: Optional[Dict[str, Any]] = None
    status: str
    last_run_at: Optional[datetime] = None


class MonitorRunCreate(BaseModel):
    """Schema for creating a new monitor run."""
    id: str = Field(..., description="Unique identifier for the monitor run")
    monitor_id: str = Field(..., description="ID of the parent monitor")
    status: Optional[str] = Field(None, description="Run status: 'running', 'completed', 'failed'")
    items_added: Optional[int] = Field(None, description="Number of items added during this run")
    items_updated: Optional[int] = Field(None, description="Number of items updated during this run")
    error_message: Optional[str] = Field(None, description="Error message if the run failed")


class MonitorRunResponse(BaseModel):
    """Schema for monitor run responses."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    monitor_id: str
    status: Optional[str] = None
    items_added: Optional[int] = None
    items_updated: Optional[int] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
