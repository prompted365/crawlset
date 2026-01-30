"""
Extraction API routes for managing extraction jobs.

Provides endpoints for submitting URLs for extraction, tracking job status,
and retrieving extraction results.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db_session
from ...database.models import ExtractionJob
from ...queue.tasks import extract_url_task, batch_extract_task
from ..schemas.extraction import ExtractionJobResponse

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# Request/Response Schemas
# ============================================================================


class ExtractURLRequest(BaseModel):
    """Request schema for single URL extraction."""
    url: str = Field(..., description="URL to extract content from")
    use_playwright: bool = Field(default=False, description="Whether to use Playwright for rendering")


class BatchExtractRequest(BaseModel):
    """Request schema for batch URL extraction."""
    urls: List[str] = Field(..., description="List of URLs to extract")
    webset_id: Optional[str] = Field(None, description="Optional webset ID to associate items with")


class ExtractURLResponse(BaseModel):
    """Response schema for extraction submission."""
    job_id: str = Field(..., description="ID of the extraction job")
    url: str = Field(..., description="URL being extracted")
    status: str = Field(..., description="Current job status")


class BatchExtractResponse(BaseModel):
    """Response schema for batch extraction submission."""
    job_id: str = Field(..., description="ID of the batch extraction job")
    total_urls: int = Field(..., description="Total number of URLs")
    status: str = Field(..., description="Current job status")


class CrawlRequest(BaseModel):
    """Request schema for full crawl with parsing."""
    url: str = Field(..., description="URL to crawl")
    use_playwright: bool = Field(default=False, description="Whether to use Playwright")


# ============================================================================
# Extraction Job Endpoints
# ============================================================================


@router.post("/extract", response_model=ExtractURLResponse, status_code=status.HTTP_201_CREATED)
async def extract_url(
    request: ExtractURLRequest,
    db: AsyncSession = Depends(get_db_session),
) -> ExtractURLResponse:
    """
    Submit a URL for extraction and return job ID.

    Args:
        request: Extraction request with URL
        db: Database session

    Returns:
        Job ID and status
    """
    try:
        # Create extraction job
        job_id = str(uuid4())
        job = ExtractionJob(
            id=job_id,
            url=request.url,
            status="pending",
            created_at=datetime.utcnow(),
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)  # Refresh to get server-generated fields

        # Submit Celery task
        logger.info(f"Submitting extraction job {job_id} for URL: {request.url}")
        extract_url_task.delay(
            url=request.url,
            job_id=job_id,
            use_playwright=request.use_playwright,
        )

        return ExtractURLResponse(
            job_id=job_id,
            url=request.url,
            status="pending",
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to submit extraction job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit extraction job: {str(e)}",
        )


@router.post("/batch", response_model=BatchExtractResponse, status_code=status.HTTP_201_CREATED)
async def batch_extract(
    request: BatchExtractRequest,
    db: AsyncSession = Depends(get_db_session),
) -> BatchExtractResponse:
    """
    Submit multiple URLs for batch extraction.

    Args:
        request: Batch extraction request
        db: Database session

    Returns:
        Job ID and status
    """
    try:
        # Create extraction job for batch
        job_id = str(uuid4())
        job = ExtractionJob(
            id=job_id,
            url=f"batch:{len(request.urls)} URLs",
            status="pending",
            created_at=datetime.utcnow(),
            result={"urls": request.urls, "webset_id": request.webset_id},
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)  # Refresh to get server-generated fields

        # Submit Celery task
        logger.info(f"Submitting batch extraction job {job_id} for {len(request.urls)} URLs")
        batch_extract_task.delay(
            urls=request.urls,
            webset_id=request.webset_id,
        )

        return BatchExtractResponse(
            job_id=job_id,
            total_urls=len(request.urls),
            status="pending",
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to submit batch extraction: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit batch extraction: {str(e)}",
        )


@router.get("/jobs/{job_id}", response_model=ExtractionJobResponse)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> ExtractionJobResponse:
    """
    Get the status of an extraction job.

    Args:
        job_id: Extraction job ID
        db: Database session

    Returns:
        Job status and details
    """
    try:
        result = await db.execute(
            select(ExtractionJob).where(ExtractionJob.id == job_id)
        )
        job = result.scalar_one_or_none()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Extraction job {job_id} not found",
            )

        return ExtractionJobResponse.model_validate(job)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status for {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}",
        )


@router.get("/jobs", response_model=List[ExtractionJobResponse])
async def list_jobs(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by job status"),
    db: AsyncSession = Depends(get_db_session),
) -> List[ExtractionJobResponse]:
    """
    List all extraction jobs with optional filtering.

    Args:
        skip: Number of items to skip
        limit: Maximum number of items to return
        status_filter: Optional status filter
        db: Database session

    Returns:
        List of extraction jobs
    """
    try:
        query = select(ExtractionJob).order_by(ExtractionJob.created_at.desc())

        if status_filter:
            query = query.where(ExtractionJob.status == status_filter)

        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        jobs = result.scalars().all()

        return [ExtractionJobResponse.model_validate(job) for job in jobs]

    except Exception as e:
        logger.error(f"Failed to list extraction jobs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list extraction jobs: {str(e)}",
        )


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """
    Cancel or delete an extraction job.

    Args:
        job_id: Extraction job ID
        db: Database session
    """
    try:
        result = await db.execute(
            select(ExtractionJob).where(ExtractionJob.id == job_id)
        )
        job = result.scalar_one_or_none()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Extraction job {job_id} not found",
            )

        # Delete job
        await db.delete(job)
        await db.commit()

        logger.info(f"Deleted extraction job: {job_id}")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete job: {str(e)}",
        )


@router.get("/jobs/{job_id}/result")
async def get_job_result(
    job_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get the extraction result for a completed job.

    Args:
        job_id: Extraction job ID
        db: Database session

    Returns:
        Extraction result data
    """
    try:
        result = await db.execute(
            select(ExtractionJob).where(ExtractionJob.id == job_id)
        )
        job = result.scalar_one_or_none()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Extraction job {job_id} not found",
            )

        if job.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job {job_id} is not completed (status: {job.status})",
            )

        if not job.result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No result available for job {job_id}",
            )

        return job.result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get result for job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job result: {str(e)}",
        )


@router.post("/crawl")
async def crawl_url(
    request: CrawlRequest,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Full crawl with parsing (synchronous for simple pages).

    This endpoint performs the extraction synchronously for pages that don't
    require JavaScript rendering. For complex pages, use the async extraction endpoint.

    Args:
        request: Crawl request
        db: Database session

    Returns:
        Extracted content
    """
    try:
        # For simple pages, execute synchronously
        if not request.use_playwright:
            logger.info(f"Synchronous crawl for URL: {request.url}")

            # Import here to avoid circular dependencies
            from ...crawler.browser import fetch_page
            from ...parser.trafilatura_parser import parse_html
            from ...preprocessing.cleaner import clean_content

            # Fetch and parse
            html = await fetch_page(request.url, use_playwright=False)
            parsed = parse_html(request.url, html)
            cleaned_text = clean_content(parsed.get("text", ""))

            return {
                "url": request.url,
                "title": parsed.get("title", ""),
                "text": cleaned_text,
                "raw_text": parsed.get("text", ""),
                "links": parsed.get("links", []),
                "metadata": {
                    "extracted_at": datetime.utcnow().isoformat(),
                    "content_length": len(cleaned_text),
                    "link_count": len(parsed.get("links", [])),
                },
            }

        else:
            # For complex pages, use async extraction
            logger.info(f"Submitting async crawl job for URL: {request.url}")

            # Create and submit job
            job_id = str(uuid4())
            job = ExtractionJob(
                id=job_id,
                url=request.url,
                status="pending",
            )
            db.add(job)
            await db.commit()

            # Submit Celery task
            extract_url_task.delay(
                url=request.url,
                job_id=job_id,
                use_playwright=True,
            )

            return {
                "job_id": job_id,
                "url": request.url,
                "status": "pending",
                "message": "Job submitted for async processing. Use GET /extraction/jobs/{job_id} to check status.",
            }

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to crawl URL {request.url}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to crawl URL: {str(e)}",
        )
