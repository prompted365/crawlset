"""
Monitor API routes for managing scheduled webset monitoring.

Provides endpoints for creating, managing, and triggering monitors with
their execution history and run details.
"""
import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db_session
from ...database.models import Monitor, MonitorRun, Webset
from ...monitors.executor import MonitorExecutor
from ...config import get_settings
from ..schemas.monitor import (
    MonitorCreate,
    MonitorUpdate,
    MonitorResponse,
    MonitorRunResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Get settings
settings = get_settings()


def get_monitor_executor() -> MonitorExecutor:
    """Dependency for MonitorExecutor."""
    return MonitorExecutor(
        db_url=settings.database_url,
        ruvector_url=settings.ruvector_url,
    )


# ============================================================================
# Request Schemas
# ============================================================================


class TriggerMonitorResponse(BaseModel):
    """Response for manual monitor trigger."""
    monitor_id: str
    status: str
    message: str


# ============================================================================
# Monitor CRUD Operations
# ============================================================================


@router.post("/", response_model=MonitorResponse, status_code=status.HTTP_201_CREATED)
async def create_monitor(
    monitor: MonitorCreate,
    db: AsyncSession = Depends(get_db_session),
) -> MonitorResponse:
    """
    Create a new monitor for a webset.

    Args:
        monitor: Monitor creation data
        db: Database session

    Returns:
        Created monitor
    """
    try:
        # Verify webset exists
        result = await db.execute(
            select(Webset).where(Webset.id == monitor.webset_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webset {monitor.webset_id} not found",
            )

        logger.info(f"Creating monitor for webset: {monitor.webset_id}")

        # Create monitor
        db_monitor = Monitor(
            id=monitor.id,
            webset_id=monitor.webset_id,
            cron_expression=monitor.cron_expression,
            timezone=monitor.timezone,
            behavior_type=monitor.behavior_type,
            behavior_config=monitor.behavior_config,
            status=monitor.status,
        )
        db.add(db_monitor)
        await db.commit()
        await db.refresh(db_monitor)

        logger.info(f"Created monitor: {db_monitor.id}")
        return MonitorResponse.model_validate(db_monitor)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create monitor: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create monitor: {str(e)}",
        )


@router.get("/", response_model=List[MonitorResponse])
async def list_monitors(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    webset_id: Optional[str] = Query(None, description="Filter by webset ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by monitor status"),
    db: AsyncSession = Depends(get_db_session),
) -> List[MonitorResponse]:
    """
    List all monitors with optional filtering.

    Args:
        skip: Number of items to skip
        limit: Maximum number of items to return
        webset_id: Optional webset ID filter
        status_filter: Optional status filter
        db: Database session

    Returns:
        List of monitors
    """
    try:
        query = select(Monitor).order_by(Monitor.last_run_at.desc().nullslast())

        if webset_id:
            query = query.where(Monitor.webset_id == webset_id)
        if status_filter:
            query = query.where(Monitor.status == status_filter)

        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        monitors = result.scalars().all()

        return [MonitorResponse.model_validate(m) for m in monitors]

    except Exception as e:
        logger.error(f"Failed to list monitors: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list monitors: {str(e)}",
        )


@router.get("/{monitor_id}", response_model=MonitorResponse)
async def get_monitor(
    monitor_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> MonitorResponse:
    """
    Get a single monitor by ID.

    Args:
        monitor_id: Monitor ID
        db: Database session

    Returns:
        Monitor details
    """
    try:
        result = await db.execute(
            select(Monitor).where(Monitor.id == monitor_id)
        )
        monitor = result.scalar_one_or_none()

        if not monitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Monitor {monitor_id} not found",
            )

        return MonitorResponse.model_validate(monitor)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get monitor {monitor_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get monitor: {str(e)}",
        )


@router.patch("/{monitor_id}", response_model=MonitorResponse)
async def update_monitor(
    monitor_id: str,
    monitor_update: MonitorUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> MonitorResponse:
    """
    Update a monitor (cron, config, status).

    Args:
        monitor_id: Monitor ID
        monitor_update: Fields to update
        db: Database session

    Returns:
        Updated monitor
    """
    try:
        # Get existing monitor
        result = await db.execute(
            select(Monitor).where(Monitor.id == monitor_id)
        )
        monitor = result.scalar_one_or_none()

        if not monitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Monitor {monitor_id} not found",
            )

        # Update fields
        update_data = monitor_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(monitor, field, value)

        await db.commit()
        await db.refresh(monitor)

        logger.info(f"Updated monitor: {monitor_id}")
        return MonitorResponse.model_validate(monitor)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update monitor {monitor_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update monitor: {str(e)}",
        )


@router.delete("/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_monitor(
    monitor_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """
    Delete a monitor.

    Args:
        monitor_id: Monitor ID
        db: Database session
    """
    try:
        result = await db.execute(
            select(Monitor).where(Monitor.id == monitor_id)
        )
        monitor = result.scalar_one_or_none()

        if not monitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Monitor {monitor_id} not found",
            )

        # Delete monitor (cascade will handle runs)
        await db.delete(monitor)
        await db.commit()

        logger.info(f"Deleted monitor: {monitor_id}")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete monitor {monitor_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete monitor: {str(e)}",
        )


# ============================================================================
# Monitor Actions
# ============================================================================


@router.post("/{monitor_id}/trigger", response_model=TriggerMonitorResponse)
async def trigger_monitor(
    monitor_id: str,
    executor: MonitorExecutor = Depends(get_monitor_executor),
    db: AsyncSession = Depends(get_db_session),
) -> TriggerMonitorResponse:
    """
    Trigger a monitor run manually.

    Args:
        monitor_id: Monitor ID
        executor: Monitor executor
        db: Database session

    Returns:
        Trigger response with status
    """
    try:
        # Verify monitor exists
        result = await db.execute(
            select(Monitor).where(Monitor.id == monitor_id)
        )
        monitor = result.scalar_one_or_none()

        if not monitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Monitor {monitor_id} not found",
            )

        logger.info(f"Manually triggering monitor: {monitor_id}")

        # Execute monitor
        result = await executor.execute_monitor(monitor_id, force=True)

        return TriggerMonitorResponse(
            monitor_id=monitor_id,
            status="completed" if not result.errors else "failed",
            message=f"Added {result.items_added}, updated {result.items_updated} items",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger monitor {monitor_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger monitor: {str(e)}",
        )


# ============================================================================
# Monitor Run History
# ============================================================================


@router.get("/{monitor_id}/runs", response_model=List[MonitorRunResponse])
async def list_monitor_runs(
    monitor_id: str,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of items to return"),
    db: AsyncSession = Depends(get_db_session),
) -> List[MonitorRunResponse]:
    """
    List monitor runs (history).

    Args:
        monitor_id: Monitor ID
        skip: Number of items to skip
        limit: Maximum number of items to return
        db: Database session

    Returns:
        List of monitor runs
    """
    try:
        # Verify monitor exists
        result = await db.execute(
            select(Monitor).where(Monitor.id == monitor_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Monitor {monitor_id} not found",
            )

        # Get runs
        result = await db.execute(
            select(MonitorRun)
            .where(MonitorRun.monitor_id == monitor_id)
            .order_by(MonitorRun.started_at.desc())
            .offset(skip)
            .limit(limit)
        )
        runs = result.scalars().all()

        return [MonitorRunResponse.model_validate(run) for run in runs]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list runs for monitor {monitor_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list monitor runs: {str(e)}",
        )


@router.get("/{monitor_id}/runs/{run_id}", response_model=MonitorRunResponse)
async def get_monitor_run(
    monitor_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> MonitorRunResponse:
    """
    Get details for a specific monitor run.

    Args:
        monitor_id: Monitor ID
        run_id: Monitor run ID
        db: Database session

    Returns:
        Monitor run details
    """
    try:
        result = await db.execute(
            select(MonitorRun).where(
                MonitorRun.id == run_id,
                MonitorRun.monitor_id == monitor_id,
            )
        )
        run = result.scalar_one_or_none()

        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Monitor run {run_id} not found for monitor {monitor_id}",
            )

        return MonitorRunResponse.model_validate(run)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get run {run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get monitor run: {str(e)}",
        )
