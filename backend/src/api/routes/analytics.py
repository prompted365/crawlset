"""
Analytics API routes for system insights and statistics.

Provides endpoints for dashboard statistics, webset insights, trending
topics/entities, and activity timeline.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db_session
from ...database.models import Webset, WebsetItem, Monitor, MonitorRun, ExtractionJob

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# Response Schemas
# ============================================================================


class DashboardStats(BaseModel):
    """Dashboard statistics response."""
    total_websets: int
    total_items: int
    total_monitors: int
    active_monitors: int
    total_extractions: int
    recent_extractions: int
    enriched_items: int
    last_updated: str


class WebsetInsight(BaseModel):
    """Webset insights response."""
    webset_id: str
    webset_name: str
    item_count: int
    enriched_count: int
    avg_content_length: Optional[float] = None
    last_updated: Optional[str] = None
    recent_activity: List[Dict[str, Any]]


class TrendingItem(BaseModel):
    """Trending topic/entity item."""
    name: str
    count: int
    change_percentage: Optional[float] = None


class TrendingResponse(BaseModel):
    """Trending topics/entities response."""
    period: str
    topics: List[TrendingItem]
    entities: List[TrendingItem]


class TimelineEvent(BaseModel):
    """Activity timeline event."""
    timestamp: str
    event_type: str
    description: str
    metadata: Dict[str, Any]


class TimelineResponse(BaseModel):
    """Activity timeline response."""
    start_date: str
    end_date: str
    total_events: int
    events: List[TimelineEvent]


# ============================================================================
# Analytics Endpoints
# ============================================================================


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db_session),
) -> DashboardStats:
    """
    Get dashboard statistics.

    Args:
        db: Database session

    Returns:
        Dashboard statistics
    """
    try:
        # Count websets
        result = await db.execute(select(func.count(Webset.id)))
        total_websets = result.scalar() or 0

        # Count items
        result = await db.execute(select(func.count(WebsetItem.id)))
        total_items = result.scalar() or 0

        # Count monitors
        result = await db.execute(select(func.count(Monitor.id)))
        total_monitors = result.scalar() or 0

        # Count active monitors
        result = await db.execute(
            select(func.count(Monitor.id)).where(Monitor.status == "enabled")
        )
        active_monitors = result.scalar() or 0

        # Count extraction jobs
        result = await db.execute(select(func.count(ExtractionJob.id)))
        total_extractions = result.scalar() or 0

        # Count recent extractions (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        result = await db.execute(
            select(func.count(ExtractionJob.id)).where(
                ExtractionJob.created_at >= yesterday
            )
        )
        recent_extractions = result.scalar() or 0

        # Count enriched items
        result = await db.execute(
            select(func.count(WebsetItem.id)).where(
                WebsetItem.enrichments.isnot(None)
            )
        )
        enriched_items = result.scalar() or 0

        return DashboardStats(
            total_websets=total_websets,
            total_items=total_items,
            total_monitors=total_monitors,
            active_monitors=active_monitors,
            total_extractions=total_extractions,
            recent_extractions=recent_extractions,
            enriched_items=enriched_items,
            last_updated=datetime.utcnow().isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to get dashboard stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard stats: {str(e)}",
        )


@router.get("/websets/{webset_id}/insights", response_model=WebsetInsight)
async def get_webset_insights(
    webset_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> WebsetInsight:
    """
    Get insights for a specific webset.

    Args:
        webset_id: Webset ID
        db: Database session

    Returns:
        Webset insights including activity and statistics
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

        # Count items
        result = await db.execute(
            select(func.count(WebsetItem.id)).where(WebsetItem.webset_id == webset_id)
        )
        item_count = result.scalar() or 0

        # Count enriched items
        result = await db.execute(
            select(func.count(WebsetItem.id)).where(
                and_(
                    WebsetItem.webset_id == webset_id,
                    WebsetItem.enrichments.isnot(None)
                )
            )
        )
        enriched_count = result.scalar() or 0

        # Get recent monitor runs for activity
        result = await db.execute(
            select(MonitorRun)
            .join(Monitor)
            .where(Monitor.webset_id == webset_id)
            .order_by(MonitorRun.started_at.desc())
            .limit(10)
        )
        runs = result.scalars().all()

        recent_activity = [
            {
                "timestamp": run.started_at.isoformat() if run.started_at else None,
                "status": run.status,
                "items_added": run.items_added,
                "items_updated": run.items_updated,
            }
            for run in runs
        ]

        return WebsetInsight(
            webset_id=webset_id,
            webset_name=webset.name,
            item_count=item_count,
            enriched_count=enriched_count,
            last_updated=webset.updated_at.isoformat() if webset.updated_at else None,
            recent_activity=recent_activity,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get webset insights for {webset_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get webset insights: {str(e)}",
        )


@router.get("/trending", response_model=TrendingResponse)
async def get_trending(
    period: str = Query("24h", description="Time period (24h, 7d, 30d)"),
    limit: int = Query(10, ge=1, le=50, description="Number of items to return"),
    db: AsyncSession = Depends(get_db_session),
) -> TrendingResponse:
    """
    Get trending topics and entities.

    Args:
        period: Time period for trending analysis
        limit: Maximum number of items to return
        db: Database session

    Returns:
        Trending topics and entities
    """
    try:
        # Parse period
        period_map = {
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
        }
        delta = period_map.get(period, timedelta(hours=24))
        start_date = datetime.utcnow() - delta

        # This is a placeholder implementation
        # In a real system, this would:
        # 1. Extract entities/topics from enrichments
        # 2. Count occurrences in the time period
        # 3. Compare with previous period for change percentage
        # 4. Rank by frequency and growth

        # For now, return mock data structure
        topics = []
        entities = []

        # Get websets by entity type to show trending categories
        result = await db.execute(
            select(Webset.entity_type, func.count(Webset.id))
            .where(
                and_(
                    Webset.entity_type.isnot(None),
                    Webset.created_at >= start_date
                )
            )
            .group_by(Webset.entity_type)
            .order_by(func.count(Webset.id).desc())
            .limit(limit)
        )
        entity_counts = result.all()

        entities = [
            TrendingItem(
                name=entity_type or "unknown",
                count=count,
            )
            for entity_type, count in entity_counts
        ]

        logger.info(f"Retrieved trending data for period: {period}")

        return TrendingResponse(
            period=period,
            topics=topics,
            entities=entities,
        )

    except Exception as e:
        logger.error(f"Failed to get trending data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trending data: {str(e)}",
        )


@router.get("/timeline", response_model=TimelineResponse)
async def get_activity_timeline(
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events"),
    db: AsyncSession = Depends(get_db_session),
) -> TimelineResponse:
    """
    Get activity timeline.

    Args:
        start_date: Optional start date
        end_date: Optional end date
        limit: Maximum number of events
        db: Database session

    Returns:
        Activity timeline with events
    """
    try:
        # Parse dates
        if start_date:
            start = datetime.fromisoformat(start_date)
        else:
            start = datetime.utcnow() - timedelta(days=7)

        if end_date:
            end = datetime.fromisoformat(end_date)
        else:
            end = datetime.utcnow()

        events = []

        # Get recent webset creations
        result = await db.execute(
            select(Webset)
            .where(
                and_(
                    Webset.created_at >= start,
                    Webset.created_at <= end
                )
            )
            .order_by(Webset.created_at.desc())
            .limit(limit // 3)
        )
        websets = result.scalars().all()

        for webset in websets:
            events.append(
                TimelineEvent(
                    timestamp=webset.created_at.isoformat() if webset.created_at else "",
                    event_type="webset_created",
                    description=f"Webset '{webset.name}' created",
                    metadata={
                        "webset_id": webset.id,
                        "entity_type": webset.entity_type,
                    },
                )
            )

        # Get recent monitor runs
        result = await db.execute(
            select(MonitorRun)
            .where(
                and_(
                    MonitorRun.started_at >= start,
                    MonitorRun.started_at <= end
                )
            )
            .order_by(MonitorRun.started_at.desc())
            .limit(limit // 3)
        )
        runs = result.scalars().all()

        for run in runs:
            events.append(
                TimelineEvent(
                    timestamp=run.started_at.isoformat() if run.started_at else "",
                    event_type="monitor_run",
                    description=f"Monitor run {run.status}",
                    metadata={
                        "run_id": run.id,
                        "monitor_id": run.monitor_id,
                        "status": run.status,
                        "items_added": run.items_added,
                        "items_updated": run.items_updated,
                    },
                )
            )

        # Get recent extraction jobs
        result = await db.execute(
            select(ExtractionJob)
            .where(
                and_(
                    ExtractionJob.created_at >= start,
                    ExtractionJob.created_at <= end
                )
            )
            .order_by(ExtractionJob.created_at.desc())
            .limit(limit // 3)
        )
        jobs = result.scalars().all()

        for job in jobs:
            events.append(
                TimelineEvent(
                    timestamp=job.created_at.isoformat() if job.created_at else "",
                    event_type="extraction_job",
                    description=f"Extraction job {job.status}",
                    metadata={
                        "job_id": job.id,
                        "url": job.url,
                        "status": job.status,
                    },
                )
            )

        # Sort all events by timestamp
        events.sort(key=lambda e: e.timestamp, reverse=True)
        events = events[:limit]

        return TimelineResponse(
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            total_events=len(events),
            events=events,
        )

    except Exception as e:
        logger.error(f"Failed to get activity timeline: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get activity timeline: {str(e)}",
        )
