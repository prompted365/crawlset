"""
Pydantic schemas for ExtractionJob model.
"""
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class ExtractionJobCreate(BaseModel):
    """Schema for creating a new extraction job."""
    id: str = Field(..., description="Unique identifier for the extraction job")
    url: str = Field(..., description="URL to extract content from")
    status: Optional[str] = Field(default="pending", description="Job status: 'pending', 'running', 'completed', 'failed'")


class ExtractionJobUpdate(BaseModel):
    """Schema for updating an existing extraction job."""
    status: Optional[str] = Field(None, description="Job status: 'pending', 'running', 'completed', 'failed'")
    result: Optional[Dict[str, Any]] = Field(None, description="Extraction result data")
    error: Optional[str] = Field(None, description="Error message if the job failed")
    completed_at: Optional[datetime] = Field(None, description="Timestamp when the job completed")


class ExtractionJobResponse(BaseModel):
    """Schema for extraction job responses."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    url: str
    status: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
