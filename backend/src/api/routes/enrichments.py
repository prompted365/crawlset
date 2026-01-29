"""
Enrichment API routes for managing content enrichment operations.

Provides endpoints for enriching webset items with LLM-extracted information,
listing available enrichment plugins, and batch enrichment operations.
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db_session
from ...database.models import WebsetItem, Webset
from ...enrichments.engine import EnrichmentEngine
from ...queue.tasks import enrich_item_task
from ...config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Get settings
settings = get_settings()


def get_enrichment_engine() -> EnrichmentEngine:
    """Dependency for EnrichmentEngine."""
    engine = EnrichmentEngine()
    # Auto-discover plugins
    try:
        engine.auto_discover_plugins("enrichments.plugins")
    except Exception as e:
        logger.warning(f"Failed to auto-discover plugins: {e}")
    return engine


# ============================================================================
# Request/Response Schemas
# ============================================================================


class EnrichItemRequest(BaseModel):
    """Request schema for enriching a single item."""
    item_id: str = Field(..., description="Webset item ID to enrich")
    plugin_names: Optional[List[str]] = Field(None, description="List of plugin names to run (default: all)")


class BatchEnrichRequest(BaseModel):
    """Request schema for batch enrichment."""
    item_ids: List[str] = Field(..., description="List of webset item IDs to enrich")
    plugin_names: Optional[List[str]] = Field(None, description="List of plugin names to run (default: all)")


class EnrichWebsetRequest(BaseModel):
    """Request schema for enriching all items in a webset."""
    plugin_names: Optional[List[str]] = Field(None, description="List of plugin names to run (default: all)")


class EnrichmentResponse(BaseModel):
    """Response schema for enrichment operations."""
    item_id: str
    status: str
    job_id: Optional[str] = None
    message: Optional[str] = None


class PluginInfoResponse(BaseModel):
    """Response schema for plugin information."""
    name: str
    schema: Dict[str, Any]


# ============================================================================
# Enrichment Operations
# ============================================================================


@router.post("/enrich", response_model=EnrichmentResponse)
async def enrich_item(
    request: EnrichItemRequest,
    db: AsyncSession = Depends(get_db_session),
) -> EnrichmentResponse:
    """
    Enrich a single webset item.

    Args:
        request: Enrichment request
        db: Database session

    Returns:
        Enrichment status and job ID
    """
    try:
        # Verify item exists
        result = await db.execute(
            select(WebsetItem).where(WebsetItem.id == request.item_id)
        )
        item = result.scalar_one_or_none()

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webset item {request.item_id} not found",
            )

        logger.info(f"Submitting enrichment job for item: {request.item_id}")

        # Submit Celery task
        task = enrich_item_task.delay(
            item_id=request.item_id,
            enrichment_types=request.plugin_names,
        )

        return EnrichmentResponse(
            item_id=request.item_id,
            status="pending",
            job_id=task.id,
            message="Enrichment job submitted successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enrich item {request.item_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enrich item: {str(e)}",
        )


@router.post("/batch", response_model=List[EnrichmentResponse])
async def batch_enrich(
    request: BatchEnrichRequest,
    db: AsyncSession = Depends(get_db_session),
) -> List[EnrichmentResponse]:
    """
    Batch enrich multiple items.

    Args:
        request: Batch enrichment request
        db: Database session

    Returns:
        List of enrichment responses
    """
    try:
        responses = []

        for item_id in request.item_ids:
            # Verify item exists
            result = await db.execute(
                select(WebsetItem).where(WebsetItem.id == item_id)
            )
            item = result.scalar_one_or_none()

            if not item:
                logger.warning(f"Item {item_id} not found, skipping")
                responses.append(
                    EnrichmentResponse(
                        item_id=item_id,
                        status="failed",
                        message=f"Item {item_id} not found",
                    )
                )
                continue

            # Submit enrichment task
            try:
                task = enrich_item_task.delay(
                    item_id=item_id,
                    enrichment_types=request.plugin_names,
                )
                responses.append(
                    EnrichmentResponse(
                        item_id=item_id,
                        status="pending",
                        job_id=task.id,
                    )
                )
            except Exception as e:
                logger.error(f"Failed to submit enrichment for item {item_id}: {e}")
                responses.append(
                    EnrichmentResponse(
                        item_id=item_id,
                        status="failed",
                        message=str(e),
                    )
                )

        logger.info(f"Submitted {len(responses)} enrichment jobs")
        return responses

    except Exception as e:
        logger.error(f"Failed to batch enrich items: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch enrich items: {str(e)}",
        )


@router.post("/websets/{webset_id}/enrich")
async def enrich_webset(
    webset_id: str,
    request: EnrichWebsetRequest,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of items to enrich"),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Enrich all items in a webset.

    Args:
        webset_id: Webset ID
        request: Enrichment request
        skip: Number of items to skip
        limit: Maximum number of items to enrich
        db: Database session

    Returns:
        Enrichment summary
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

        # Get all items in webset
        result = await db.execute(
            select(WebsetItem)
            .where(WebsetItem.webset_id == webset_id)
            .offset(skip)
            .limit(limit)
        )
        items = result.scalars().all()

        if not items:
            return {
                "webset_id": webset_id,
                "total_items": 0,
                "submitted_jobs": 0,
                "message": "No items found in webset",
            }

        # Submit enrichment jobs
        submitted = 0
        failed = 0

        for item in items:
            try:
                enrich_item_task.delay(
                    item_id=item.id,
                    enrichment_types=request.plugin_names,
                )
                submitted += 1
            except Exception as e:
                logger.error(f"Failed to submit enrichment for item {item.id}: {e}")
                failed += 1

        logger.info(f"Submitted {submitted} enrichment jobs for webset {webset_id}")

        return {
            "webset_id": webset_id,
            "total_items": len(items),
            "submitted_jobs": submitted,
            "failed_jobs": failed,
            "message": f"Submitted {submitted} enrichment jobs",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enrich webset {webset_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enrich webset: {str(e)}",
        )


# ============================================================================
# Plugin Management
# ============================================================================


@router.get("/plugins", response_model=List[PluginInfoResponse])
async def list_plugins(
    engine: EnrichmentEngine = Depends(get_enrichment_engine),
) -> List[PluginInfoResponse]:
    """
    List available enrichment plugins.

    Args:
        engine: Enrichment engine

    Returns:
        List of available plugins with their schemas
    """
    try:
        plugins = engine.list_plugins()
        return [
            PluginInfoResponse(
                name=plugin["name"],
                schema=plugin["schema"],
            )
            for plugin in plugins
        ]

    except Exception as e:
        logger.error(f"Failed to list enrichment plugins: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list plugins: {str(e)}",
        )


@router.get("/plugins/{plugin_id}")
async def get_plugin_details(
    plugin_id: str,
    engine: EnrichmentEngine = Depends(get_enrichment_engine),
) -> Dict[str, Any]:
    """
    Get details for a specific enrichment plugin.

    Args:
        plugin_id: Plugin name/ID
        engine: Enrichment engine

    Returns:
        Plugin details including schema and configuration
    """
    try:
        plugin = engine.get_plugin(plugin_id)

        if not plugin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plugin {plugin_id} not found",
            )

        return {
            "name": plugin.name,
            "schema": plugin.get_schema(),
            "config": plugin.config,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get plugin details for {plugin_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get plugin details: {str(e)}",
        )
