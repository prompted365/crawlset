"""
Export API routes for exporting webset data in various formats.

Provides endpoints for exporting webset data as JSON, CSV, and Markdown.
"""
import csv
import io
import json
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db_session
from ...database.models import Webset, WebsetItem

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# Export Utilities
# ============================================================================


def items_to_json(webset: Webset, items: List[WebsetItem]) -> str:
    """
    Convert webset and items to JSON format.

    Args:
        webset: Webset model
        items: List of webset items

    Returns:
        JSON string
    """
    data = {
        "webset": {
            "id": webset.id,
            "name": webset.name,
            "search_query": webset.search_query,
            "search_criteria": webset.search_criteria,
            "entity_type": webset.entity_type,
            "created_at": webset.created_at.isoformat() if webset.created_at else None,
            "updated_at": webset.updated_at.isoformat() if webset.updated_at else None,
        },
        "items": [
            {
                "id": item.id,
                "url": item.url,
                "title": item.title,
                "content_hash": item.content_hash,
                "metadata": item.metadata,
                "enrichments": item.enrichments,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ],
        "total_items": len(items),
    }
    return json.dumps(data, indent=2)


def items_to_csv(items: List[WebsetItem]) -> str:
    """
    Convert items to CSV format.

    Args:
        items: List of webset items

    Returns:
        CSV string
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        "id",
        "url",
        "title",
        "content_hash",
        "metadata",
        "enrichments",
        "created_at",
    ])

    # Write rows
    for item in items:
        writer.writerow([
            item.id,
            item.url,
            item.title or "",
            item.content_hash or "",
            json.dumps(item.metadata) if item.metadata else "",
            json.dumps(item.enrichments) if item.enrichments else "",
            item.created_at.isoformat() if item.created_at else "",
        ])

    return output.getvalue()


def items_to_markdown(webset: Webset, items: List[WebsetItem]) -> str:
    """
    Convert webset and items to Markdown format.

    Args:
        webset: Webset model
        items: List of webset items

    Returns:
        Markdown string
    """
    lines = []

    # Webset header
    lines.append(f"# {webset.name}")
    lines.append("")

    if webset.search_query:
        lines.append(f"**Search Query:** {webset.search_query}")
        lines.append("")

    if webset.entity_type:
        lines.append(f"**Entity Type:** {webset.entity_type}")
        lines.append("")

    lines.append(f"**Total Items:** {len(items)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Items
    for i, item in enumerate(items, 1):
        lines.append(f"## {i}. {item.title or 'Untitled'}")
        lines.append("")
        lines.append(f"**URL:** {item.url}")
        lines.append("")

        # Add metadata if available
        if item.metadata:
            lines.append("**Metadata:**")
            lines.append("")
            try:
                metadata = item.metadata if isinstance(item.metadata, dict) else json.loads(item.metadata)
                for key, value in metadata.items():
                    lines.append(f"- **{key}:** {value}")
                lines.append("")
            except Exception:
                pass

        # Add enrichments if available
        if item.enrichments:
            lines.append("**Enrichments:**")
            lines.append("")
            try:
                enrichments = item.enrichments if isinstance(item.enrichments, dict) else json.loads(item.enrichments)
                for key, value in enrichments.items():
                    lines.append(f"- **{key}:** {value}")
                lines.append("")
            except Exception:
                pass

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


# ============================================================================
# Export Endpoints
# ============================================================================


@router.get("/websets/{webset_id}/json")
async def export_json(
    webset_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """
    Export webset as JSON.

    Args:
        webset_id: Webset ID
        db: Database session

    Returns:
        JSON file download
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

        # Get all items
        result = await db.execute(
            select(WebsetItem)
            .where(WebsetItem.webset_id == webset_id)
            .order_by(WebsetItem.created_at.desc())
        )
        items = result.scalars().all()

        # Convert to JSON
        json_data = items_to_json(webset, items)

        # Return as downloadable file
        filename = f"{webset.name.replace(' ', '_')}_export.json"
        return Response(
            content=json_data,
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export webset {webset_id} as JSON: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export as JSON: {str(e)}",
        )


@router.get("/websets/{webset_id}/csv")
async def export_csv(
    webset_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """
    Export webset as CSV.

    Args:
        webset_id: Webset ID
        db: Database session

    Returns:
        CSV file download
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

        # Get all items
        result = await db.execute(
            select(WebsetItem)
            .where(WebsetItem.webset_id == webset_id)
            .order_by(WebsetItem.created_at.desc())
        )
        items = result.scalars().all()

        # Convert to CSV
        csv_data = items_to_csv(items)

        # Return as downloadable file
        filename = f"{webset.name.replace(' ', '_')}_export.csv"
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export webset {webset_id} as CSV: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export as CSV: {str(e)}",
        )


@router.get("/websets/{webset_id}/markdown")
async def export_markdown(
    webset_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """
    Export webset as Markdown.

    Args:
        webset_id: Webset ID
        db: Database session

    Returns:
        Markdown file download
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

        # Get all items
        result = await db.execute(
            select(WebsetItem)
            .where(WebsetItem.webset_id == webset_id)
            .order_by(WebsetItem.created_at.desc())
        )
        items = result.scalars().all()

        # Convert to Markdown
        markdown_data = items_to_markdown(webset, items)

        # Return as downloadable file
        filename = f"{webset.name.replace(' ', '_')}_export.md"
        return Response(
            content=markdown_data,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export webset {webset_id} as Markdown: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export as Markdown: {str(e)}",
        )
