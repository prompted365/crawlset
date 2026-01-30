"""
Webset API routes with complete CRUD operations.

Provides endpoints for managing websets, their items, and associated operations
including search, enrichment, and statistics.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db_session
from ...database.models import Webset, WebsetItem
from ...websets.manager import WebsetManager
from ...monitors.executor import MonitorExecutor
from ...config import get_settings
from ..schemas.webset import (
    WebsetCreate,
    WebsetUpdate,
    WebsetResponse,
    WebsetItemCreate,
    WebsetItemResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Get settings
settings = get_settings()


def get_webset_manager() -> WebsetManager:
    """Dependency for WebsetManager."""
    return WebsetManager(db_url=settings.database_url)


def get_monitor_executor() -> MonitorExecutor:
    """Dependency for MonitorExecutor."""
    return MonitorExecutor(
        db_url=settings.database_url,
        ruvector_url=settings.ruvector_url,
    )


# ============================================================================
# Webset CRUD Operations
# ============================================================================


@router.post("/", response_model=WebsetResponse, status_code=status.HTTP_201_CREATED)
async def create_webset(
    webset: WebsetCreate,
    db: AsyncSession = Depends(get_db_session),
) -> WebsetResponse:
    """
    Create a new webset.

    Args:
        webset: Webset creation data
        db: Database session

    Returns:
        Created webset
    """
    try:
        logger.info(f"Creating webset: {webset.name}")

        # Auto-generate ID if not provided
        webset_id = webset.id or str(uuid4())

        # Create webset in database
        db_webset = Webset(
            id=webset_id,
            name=webset.name,
            search_query=webset.search_query,
            search_criteria=webset.search_criteria,
            entity_type=webset.entity_type,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(db_webset)
        await db.commit()
        await db.refresh(db_webset)

        logger.info(f"Created webset: {db_webset.id}")
        return WebsetResponse.model_validate(db_webset)

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create webset: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create webset: {str(e)}",
        )


@router.get("/", response_model=List[WebsetResponse])
async def list_websets(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    search_query: Optional[str] = Query(None, description="Filter by search query"),
    db: AsyncSession = Depends(get_db_session),
) -> List[WebsetResponse]:
    """
    List all websets with pagination and filtering.

    Args:
        skip: Number of items to skip (offset)
        limit: Maximum number of items to return
        entity_type: Optional filter by entity type
        search_query: Optional filter by search query
        db: Database session

    Returns:
        List of websets
    """
    try:
        # Build query with filters
        query = select(Webset).order_by(Webset.updated_at.desc())

        if entity_type:
            query = query.where(Webset.entity_type == entity_type)
        if search_query:
            query = query.where(Webset.search_query.ilike(f"%{search_query}%"))

        query = query.offset(skip).limit(limit)

        # Execute query
        result = await db.execute(query)
        websets = result.scalars().all()

        return [WebsetResponse.model_validate(w) for w in websets]

    except Exception as e:
        logger.error(f"Failed to list websets: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list websets: {str(e)}",
        )


@router.get("/{webset_id}", response_model=WebsetResponse)
async def get_webset(
    webset_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> WebsetResponse:
    """
    Get a single webset by ID.

    Args:
        webset_id: Webset ID
        db: Database session

    Returns:
        Webset details
    """
    try:
        result = await db.execute(
            select(Webset).where(Webset.id == webset_id)
        )
        webset = result.scalar_one_or_none()

        if not webset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webset {webset_id} not found",
            )

        return WebsetResponse.model_validate(webset)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get webset {webset_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get webset: {str(e)}",
        )


@router.patch("/{webset_id}", response_model=WebsetResponse)
async def update_webset(
    webset_id: str,
    webset_update: WebsetUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> WebsetResponse:
    """
    Update a webset.

    Args:
        webset_id: Webset ID
        webset_update: Fields to update
        db: Database session

    Returns:
        Updated webset
    """
    try:
        # Get existing webset
        result = await db.execute(
            select(Webset).where(Webset.id == webset_id)
        )
        webset = result.scalar_one_or_none()

        if not webset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webset {webset_id} not found",
            )

        # Update fields
        update_data = webset_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(webset, field, value)

        await db.commit()
        await db.refresh(webset)

        logger.info(f"Updated webset: {webset_id}")
        return WebsetResponse.model_validate(webset)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update webset {webset_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update webset: {str(e)}",
        )


@router.delete("/{webset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webset(
    webset_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """
    Delete a webset and all its items.

    Args:
        webset_id: Webset ID
        db: Database session
    """
    try:
        # Get webset
        result = await db.execute(
            select(Webset).where(Webset.id == webset_id)
        )
        webset = result.scalar_one_or_none()

        if not webset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webset {webset_id} not found",
            )

        # Delete webset (cascade will handle items and monitors)
        await db.delete(webset)
        await db.commit()

        logger.info(f"Deleted webset: {webset_id}")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete webset {webset_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete webset: {str(e)}",
        )


# ============================================================================
# Webset Item Operations
# ============================================================================


@router.get("/{webset_id}/items", response_model=List[WebsetItemResponse])
async def list_webset_items(
    webset_id: str,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    db: AsyncSession = Depends(get_db_session),
) -> List[WebsetItemResponse]:
    """
    List items in a webset with pagination.

    Args:
        webset_id: Webset ID
        skip: Number of items to skip
        limit: Maximum number of items to return
        db: Database session

    Returns:
        List of webset items
    """
    try:
        # Verify webset exists
        result = await db.execute(
            select(Webset).where(Webset.id == webset_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webset {webset_id} not found",
            )

        # Get items
        result = await db.execute(
            select(WebsetItem)
            .where(WebsetItem.webset_id == webset_id)
            .order_by(WebsetItem.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        items = result.scalars().all()

        return [WebsetItemResponse.model_validate(item) for item in items]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list items for webset {webset_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list items: {str(e)}",
        )


@router.post("/{webset_id}/items", response_model=WebsetItemResponse, status_code=status.HTTP_201_CREATED)
async def add_webset_item(
    webset_id: str,
    item: WebsetItemCreate,
    db: AsyncSession = Depends(get_db_session),
) -> WebsetItemResponse:
    """
    Add an item to a webset.

    Args:
        webset_id: Webset ID
        item: Item data
        db: Database session

    Returns:
        Created item
    """
    try:
        # Verify webset exists
        result = await db.execute(
            select(Webset).where(Webset.id == webset_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webset {webset_id} not found",
            )

        # Create item
        db_item = WebsetItem(
            id=item.id,
            webset_id=webset_id,
            url=item.url,
            title=item.title,
            content_hash=item.content_hash,
            metadata=item.metadata,
            enrichments=item.enrichments,
            astradb_doc_id=item.astradb_doc_id,
        )
        db.add(db_item)
        await db.commit()
        await db.refresh(db_item)

        logger.info(f"Added item {db_item.id} to webset {webset_id}")
        return WebsetItemResponse.model_validate(db_item)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to add item to webset {webset_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add item: {str(e)}",
        )


@router.delete("/{webset_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webset_item(
    webset_id: str,
    item_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """
    Remove an item from a webset.

    Args:
        webset_id: Webset ID
        item_id: Item ID
        db: Database session
    """
    try:
        # Get item
        result = await db.execute(
            select(WebsetItem).where(
                WebsetItem.id == item_id,
                WebsetItem.webset_id == webset_id,
            )
        )
        item = result.scalar_one_or_none()

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item {item_id} not found in webset {webset_id}",
            )

        # Delete item
        await db.delete(item)
        await db.commit()

        logger.info(f"Deleted item {item_id} from webset {webset_id}")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete item {item_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete item: {str(e)}",
        )


# ============================================================================
# Webset Search and Actions
# ============================================================================


@router.post("/{webset_id}/search")
async def execute_webset_search(
    webset_id: str,
    executor: MonitorExecutor = Depends(get_monitor_executor),
) -> Dict[str, Any]:
    """
    Execute search and populate webset with results.

    Args:
        webset_id: Webset ID
        executor: Monitor executor

    Returns:
        Search execution results
    """
    try:
        logger.info(f"Executing search for webset {webset_id}")

        # Execute as a one-time behavior
        result = await executor.execute_webset(
            webset_id=webset_id,
            behavior_type="search",
        )

        return {
            "webset_id": webset_id,
            "items_added": result.items_added,
            "items_updated": result.items_updated,
            "errors": result.errors,
        }

    except Exception as e:
        logger.error(f"Failed to execute search for webset {webset_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute search: {str(e)}",
        )


# ============================================================================
# Webset Statistics
# ============================================================================


@router.get("/{webset_id}/stats")
async def get_webset_stats(
    webset_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get statistics for a webset.

    Args:
        webset_id: Webset ID
        db: Database session

    Returns:
        Webset statistics (item count, last updated, etc.)
    """
    try:
        # Verify webset exists
        result = await db.execute(
            select(Webset).where(Webset.id == webset_id)
        )
        webset = result.scalar_one_or_none()

        if not webset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webset {webset_id} not found",
            )

        # Get item count
        result = await db.execute(
            select(func.count(WebsetItem.id)).where(WebsetItem.webset_id == webset_id)
        )
        item_count = result.scalar() or 0

        # Get enriched item count
        result = await db.execute(
            select(func.count(WebsetItem.id)).where(
                WebsetItem.webset_id == webset_id,
                WebsetItem.enrichments.isnot(None),
            )
        )
        enriched_count = result.scalar() or 0

        return {
            "webset_id": webset_id,
            "name": webset.name,
            "item_count": item_count,
            "enriched_count": enriched_count,
            "entity_type": webset.entity_type,
            "created_at": webset.created_at.isoformat() if webset.created_at else None,
            "updated_at": webset.updated_at.isoformat() if webset.updated_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get stats for webset {webset_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get webset stats: {str(e)}",
        )
