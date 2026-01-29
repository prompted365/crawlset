"""
Pydantic schemas for Webset and WebsetItem models.
"""
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class WebsetCreate(BaseModel):
    """Schema for creating a new webset."""
    id: str = Field(..., description="Unique identifier for the webset")
    name: str = Field(..., description="Human-readable name for the webset")
    search_query: Optional[str] = Field(None, description="Search query used to populate the webset")
    search_criteria: Optional[Dict[str, Any]] = Field(None, description="Structured search criteria")
    entity_type: Optional[str] = Field(None, description="Type of entities in the webset (e.g., 'podcast', 'company')")


class WebsetUpdate(BaseModel):
    """Schema for updating an existing webset."""
    name: Optional[str] = Field(None, description="Human-readable name for the webset")
    search_query: Optional[str] = Field(None, description="Search query used to populate the webset")
    search_criteria: Optional[Dict[str, Any]] = Field(None, description="Structured search criteria")
    entity_type: Optional[str] = Field(None, description="Type of entities in the webset")


class WebsetResponse(BaseModel):
    """Schema for webset responses."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    search_query: Optional[str] = None
    search_criteria: Optional[Dict[str, Any]] = None
    entity_type: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class WebsetItemCreate(BaseModel):
    """Schema for creating a new webset item."""
    id: str = Field(..., description="Unique identifier for the webset item")
    webset_id: str = Field(..., description="ID of the parent webset")
    url: str = Field(..., description="URL of the web content")
    title: Optional[str] = Field(None, description="Title of the web content")
    content_hash: Optional[str] = Field(None, description="Hash of the content for deduplication")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Extracted metadata from the content")
    enrichments: Optional[Dict[str, Any]] = Field(None, description="LLM-generated enrichments")
    astradb_doc_id: Optional[str] = Field(None, description="Document ID in AstraDB vector database")


class WebsetItemResponse(BaseModel):
    """Schema for webset item responses."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    webset_id: str
    url: str
    title: Optional[str] = None
    content_hash: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    enrichments: Optional[Dict[str, Any]] = None
    astradb_doc_id: Optional[str] = None
    created_at: datetime
