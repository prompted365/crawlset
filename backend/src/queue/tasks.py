"""
Celery tasks for distributed processing in the intelligence pipeline.

Tasks:
- extract_url_task: Extract content from a single URL
- batch_extract_task: Process multiple URLs in batch
- process_webset_task: Process webset search/refresh
- run_monitor_task: Execute monitor and update items
- enrich_item_task: Run enrichments on items
- cleanup_expired_results: Periodic cleanup task
"""

from __future__ import annotations
import asyncio
import datetime
import hashlib
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded, Retry
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .celery_app import app
from ..crawler.browser import fetch_page
from ..parser.trafilatura_parser import parse_html
from ..preprocessing.chunker import chunk_text, ChunkingStrategy
from ..preprocessing.cleaner import clean_content
from ..ruvector.client import RuVectorClient

logger = logging.getLogger(__name__)

# Database connection helper
def _get_db_connection(db_path: str = None) -> sqlite3.Connection:
    """Get SQLite database connection."""
    import os
    db_path = db_path or os.getenv("SQLITE_DB", "./data/websets.db")
    return sqlite3.connect(db_path)


# Custom task class with error handling
class CallbackTask(Task):
    """Base task class with built-in error handling and callbacks."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Log task failure and store in database."""
        logger.error(f"Task {task_id} failed: {exc}")
        # Store failure in extraction_jobs if applicable
        if hasattr(self, '_store_failure'):
            self._store_failure(task_id, str(exc))

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Log task retry."""
        logger.warning(f"Task {task_id} retrying: {exc}")

    def on_success(self, retval, task_id, args, kwargs):
        """Log task success."""
        logger.info(f"Task {task_id} completed successfully")


@app.task(
    bind=True,
    base=CallbackTask,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    acks_late=True,
    reject_on_worker_lost=True,
)
def extract_url_task(self, url: str, job_id: Optional[str] = None, use_playwright: bool = False) -> Dict[str, Any]:
    """
    Extract content from a single URL.

    Args:
        url: URL to extract
        job_id: Optional extraction job ID for tracking
        use_playwright: Whether to use Playwright for rendering

    Returns:
        Dict with extracted content (title, text, links, metadata)

    Raises:
        Exception: On extraction failure after retries
    """
    try:
        # Update job status to processing
        if job_id:
            with _get_db_connection() as conn:
                conn.execute(
                    "UPDATE extraction_jobs SET status=? WHERE id=?",
                    ("processing", job_id)
                )
                conn.commit()

        # Update task state
        self.update_state(state="PROGRESS", meta={"status": "fetching", "url": url})

        # Fetch page (async function, need to run in event loop)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        html = loop.run_until_complete(fetch_page(url, use_playwright=use_playwright))

        self.update_state(state="PROGRESS", meta={"status": "parsing", "url": url})

        # Parse HTML
        parsed = parse_html(url, html)

        # Clean content
        cleaned_text = clean_content(parsed.get("text", ""))

        # Create result
        result = {
            "url": url,
            "title": parsed.get("title", ""),
            "text": cleaned_text,
            "raw_text": parsed.get("text", ""),
            "links": parsed.get("links", []),
            "metadata": {
                "extracted_at": datetime.datetime.utcnow().isoformat(),
                "use_playwright": use_playwright,
                "content_length": len(cleaned_text),
                "link_count": len(parsed.get("links", [])),
            }
        }

        # Update job status to completed
        if job_id:
            with _get_db_connection() as conn:
                conn.execute(
                    "UPDATE extraction_jobs SET status=?, result=?, completed_at=? WHERE id=?",
                    ("completed", json.dumps(result), datetime.datetime.utcnow().isoformat(), job_id)
                )
                conn.commit()

        return result

    except SoftTimeLimitExceeded:
        logger.error(f"Task time limit exceeded for URL: {url}")
        if job_id:
            with _get_db_connection() as conn:
                conn.execute(
                    "UPDATE extraction_jobs SET status=?, error=?, completed_at=? WHERE id=?",
                    ("failed", "Time limit exceeded", datetime.datetime.utcnow().isoformat(), job_id)
                )
                conn.commit()
        raise

    except Exception as exc:
        logger.error(f"Failed to extract URL {url}: {exc}")
        if job_id:
            with _get_db_connection() as conn:
                conn.execute(
                    "UPDATE extraction_jobs SET status=?, error=?, completed_at=? WHERE id=?",
                    ("failed", str(exc), datetime.datetime.utcnow().isoformat(), job_id)
                )
                conn.commit()
        raise


@app.task(
    bind=True,
    base=CallbackTask,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2},
    retry_backoff=True,
    acks_late=True,
)
def batch_extract_task(self, urls: List[str], webset_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Process multiple URLs in batch.

    Args:
        urls: List of URLs to extract
        webset_id: Optional webset ID to associate items with

    Returns:
        Dict with summary (total, successful, failed, items)
    """
    total = len(urls)
    successful = 0
    failed = 0
    results = []

    self.update_state(state="PROGRESS", meta={"status": "processing", "total": total, "completed": 0})

    for idx, url in enumerate(urls):
        try:
            # Call extract_url_task synchronously
            result = extract_url_task.apply(args=[url]).get()
            results.append(result)
            successful += 1

            # If webset_id provided, store in database
            if webset_id:
                _store_webset_item(webset_id, result)

        except Exception as exc:
            logger.error(f"Failed to extract URL {url} in batch: {exc}")
            failed += 1
            results.append({"url": url, "error": str(exc)})

        # Update progress
        self.update_state(
            state="PROGRESS",
            meta={
                "status": "processing",
                "total": total,
                "completed": idx + 1,
                "successful": successful,
                "failed": failed,
            }
        )

    return {
        "total": total,
        "successful": successful,
        "failed": failed,
        "items": results,
    }


@app.task(
    bind=True,
    base=CallbackTask,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2},
    retry_backoff=True,
    acks_late=True,
)
def process_webset_task(self, webset_id: str, action: str = "refresh") -> Dict[str, Any]:
    """
    Process webset search or refresh.

    Args:
        webset_id: Webset ID to process
        action: Action to perform (refresh, search, etc.)

    Returns:
        Dict with processing summary
    """
    try:
        self.update_state(state="PROGRESS", meta={"status": "loading_webset", "webset_id": webset_id})

        with _get_db_connection() as conn:
            # Load webset
            cur = conn.execute(
                "SELECT id, name, search_query, search_criteria FROM websets WHERE id=?",
                (webset_id,)
            )
            webset_row = cur.fetchone()

            if not webset_row:
                raise ValueError(f"Webset {webset_id} not found")

            # Load existing items
            cur = conn.execute(
                "SELECT id, url, content_hash FROM webset_items WHERE webset_id=?",
                (webset_id,)
            )
            items = cur.fetchall()

        items_updated = 0
        items_added = 0
        items_failed = 0

        self.update_state(
            state="PROGRESS",
            meta={"status": "processing_items", "total": len(items), "completed": 0}
        )

        # Process each item
        for idx, (item_id, url, old_hash) in enumerate(items):
            try:
                # Extract content
                result = extract_url_task.apply(args=[url]).get()

                # Calculate content hash
                content = result.get("text", "")
                content_hash = hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()

                # Update if content changed
                if content_hash != old_hash:
                    with _get_db_connection() as conn:
                        conn.execute(
                            """UPDATE webset_items
                               SET content=?, content_hash=?, title=?, metadata=?, last_crawled_at=?
                               WHERE id=?""",
                            (
                                content,
                                content_hash,
                                result.get("title", ""),
                                json.dumps(result.get("metadata", {})),
                                datetime.datetime.utcnow().isoformat(),
                                item_id
                            )
                        )
                        conn.commit()
                    items_updated += 1
                else:
                    # Just update last_crawled_at
                    with _get_db_connection() as conn:
                        conn.execute(
                            "UPDATE webset_items SET last_crawled_at=? WHERE id=?",
                            (datetime.datetime.utcnow().isoformat(), item_id)
                        )
                        conn.commit()

            except Exception as exc:
                logger.error(f"Failed to process item {item_id}: {exc}")
                items_failed += 1

            self.update_state(
                state="PROGRESS",
                meta={
                    "status": "processing_items",
                    "total": len(items),
                    "completed": idx + 1,
                    "updated": items_updated,
                    "failed": items_failed,
                }
            )

        # Update webset timestamp
        with _get_db_connection() as conn:
            conn.execute(
                "UPDATE websets SET updated_at=? WHERE id=?",
                (datetime.datetime.utcnow().isoformat(), webset_id)
            )
            conn.commit()

        return {
            "webset_id": webset_id,
            "action": action,
            "total_items": len(items),
            "items_updated": items_updated,
            "items_added": items_added,
            "items_failed": items_failed,
        }

    except Exception as exc:
        logger.error(f"Failed to process webset {webset_id}: {exc}")
        raise


@app.task(
    bind=True,
    base=CallbackTask,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2},
    retry_backoff=True,
    acks_late=True,
)
def run_monitor_task(self, monitor_id: str) -> Dict[str, Any]:
    """
    Execute a monitor and update associated webset items.

    Args:
        monitor_id: Monitor ID to execute

    Returns:
        Dict with execution summary
    """
    try:
        self.update_state(state="PROGRESS", meta={"status": "loading_monitor", "monitor_id": monitor_id})

        with _get_db_connection() as conn:
            # Load monitor
            cur = conn.execute(
                "SELECT webset_id, behavior_type, behavior_config FROM monitors WHERE id=? AND status='enabled'",
                (monitor_id,)
            )
            monitor_row = cur.fetchone()

            if not monitor_row:
                raise ValueError(f"Monitor {monitor_id} not found or disabled")

            webset_id, behavior_type, behavior_config = monitor_row

            # Create monitor run record
            run_id = f"run-{monitor_id}-{datetime.datetime.utcnow().isoformat()}"
            conn.execute(
                """INSERT INTO monitor_runs
                   (id, monitor_id, status, items_added, items_updated, started_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (run_id, monitor_id, "running", 0, 0, datetime.datetime.utcnow().isoformat())
            )
            conn.commit()

        # Execute webset processing
        result = process_webset_task.apply(args=[webset_id, behavior_type or "refresh"]).get()

        # Update monitor run record
        with _get_db_connection() as conn:
            conn.execute(
                """UPDATE monitor_runs
                   SET status=?, items_added=?, items_updated=?, completed_at=?
                   WHERE id=?""",
                (
                    "completed",
                    result.get("items_added", 0),
                    result.get("items_updated", 0),
                    datetime.datetime.utcnow().isoformat(),
                    run_id
                )
            )
            # Update monitor last_run_at
            conn.execute(
                "UPDATE monitors SET last_run_at=? WHERE id=?",
                (datetime.datetime.utcnow().isoformat(), monitor_id)
            )
            conn.commit()

        return {
            "monitor_id": monitor_id,
            "run_id": run_id,
            "result": result,
        }

    except Exception as exc:
        logger.error(f"Failed to run monitor {monitor_id}: {exc}")

        # Update monitor run record with error
        with _get_db_connection() as conn:
            conn.execute(
                """UPDATE monitor_runs
                   SET status=?, error_message=?, completed_at=?
                   WHERE monitor_id=? AND status='running'""",
                ("failed", str(exc), datetime.datetime.utcnow().isoformat(), monitor_id)
            )
            conn.commit()

        raise


@app.task(
    bind=True,
    base=CallbackTask,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3},
    retry_backoff=True,
    acks_late=True,
)
def enrich_item_task(self, item_id: str, enrichment_types: List[str] = None) -> Dict[str, Any]:
    """
    Run enrichments on a webset item.

    Args:
        item_id: Webset item ID
        enrichment_types: List of enrichment types to run (e.g., ['entities', 'sentiment', 'summary'])

    Returns:
        Dict with enrichment results
    """
    try:
        self.update_state(state="PROGRESS", meta={"status": "loading_item", "item_id": item_id})

        with _get_db_connection() as conn:
            cur = conn.execute(
                "SELECT url, title, content, enrichments FROM webset_items WHERE id=?",
                (item_id,)
            )
            item_row = cur.fetchone()

            if not item_row:
                raise ValueError(f"Item {item_id} not found")

            url, title, content, existing_enrichments = item_row

            # Parse existing enrichments
            try:
                enrichments = json.loads(existing_enrichments) if existing_enrichments else {}
            except:
                enrichments = {}

        # Default enrichment types
        if not enrichment_types:
            enrichment_types = ["summary", "keywords", "entities"]

        # Run enrichments (placeholder - implement actual enrichment logic)
        for enrichment_type in enrichment_types:
            self.update_state(
                state="PROGRESS",
                meta={"status": f"running_{enrichment_type}", "item_id": item_id}
            )

            if enrichment_type == "summary":
                # TODO: Implement LLM-based summarization
                enrichments["summary"] = content[:500] + "..." if len(content) > 500 else content

            elif enrichment_type == "keywords":
                # TODO: Implement keyword extraction
                enrichments["keywords"] = []

            elif enrichment_type == "entities":
                # TODO: Implement entity extraction
                enrichments["entities"] = []

        # Store enrichments
        with _get_db_connection() as conn:
            conn.execute(
                "UPDATE webset_items SET enrichments=? WHERE id=?",
                (json.dumps(enrichments), item_id)
            )
            conn.commit()

        return {
            "item_id": item_id,
            "enrichment_types": enrichment_types,
            "enrichments": enrichments,
        }

    except Exception as exc:
        logger.error(f"Failed to enrich item {item_id}: {exc}")
        raise


@app.task(bind=True, base=CallbackTask)
def cleanup_expired_results(self):
    """
    Periodic task to clean up expired results and old extraction jobs.
    """
    try:
        cutoff_date = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).isoformat()

        with _get_db_connection() as conn:
            # Delete old completed extraction jobs
            cur = conn.execute(
                "DELETE FROM extraction_jobs WHERE status='completed' AND completed_at < ?",
                (cutoff_date,)
            )
            deleted_count = cur.rowcount
            conn.commit()

        logger.info(f"Cleaned up {deleted_count} expired extraction jobs")

        return {
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date,
        }

    except Exception as exc:
        logger.error(f"Failed to clean up expired results: {exc}")
        raise


# Helper functions

def _store_webset_item(webset_id: str, extracted_data: Dict[str, Any]) -> str:
    """Store extracted data as webset item."""
    import uuid

    item_id = str(uuid.uuid4())
    url = extracted_data.get("url", "")
    title = extracted_data.get("title", "")
    content = extracted_data.get("text", "")
    content_hash = hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()
    metadata = json.dumps(extracted_data.get("metadata", {}))

    with _get_db_connection() as conn:
        conn.execute(
            """INSERT INTO webset_items
               (id, webset_id, url, title, content, content_hash, metadata, created_at, last_crawled_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item_id,
                webset_id,
                url,
                title,
                content,
                content_hash,
                metadata,
                datetime.datetime.utcnow().isoformat(),
                datetime.datetime.utcnow().isoformat(),
            )
        )
        conn.commit()

    return item_id


# ============================================================================
# Operation Torque Synergies: SONA + GNN Self-Learning Tasks
# ============================================================================


@app.task(
    bind=True,
    base=CallbackTask,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2},
    retry_backoff=True,
    acks_late=True,
)
def send_sona_trajectory_task(
    self,
    actions: List[Dict[str, Any]],
    reward: float,
    trajectory_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Send extraction trajectory data to RuVector SONA for self-learning.

    After successful extraction jobs, this task reports the sequence of
    actions taken (fetch, parse, enrich) and the resulting reward signal
    so RuVector's Self-Organizing Neural Architecture can learn which
    extraction patterns work best and improve future crawl quality.

    Args:
        actions: List of action dicts describing the extraction trajectory
                 e.g. [{"type": "fetch", "url": "...", "success": True}, ...]
        reward: Reward signal (0.0 to 1.0) indicating extraction quality
        trajectory_metadata: Optional metadata about the trajectory

    Returns:
        Dict with SONA response
    """
    import os

    try:
        self.update_state(state="PROGRESS", meta={"status": "sending_sona_trajectory"})

        ruvector_url = os.environ.get("RUVECTOR_URL", "http://localhost:6333")

        # Use synchronous HTTP for Celery worker context
        import httpx

        with httpx.Client(base_url=ruvector_url, timeout=30.0) as client:
            response = client.post(
                "/sona/trajectory",
                json={
                    "actions": actions,
                    "reward": reward,
                    "metadata": trajectory_metadata or {},
                },
            )
            response.raise_for_status()
            result = response.json()

        logger.info(f"SONA trajectory sent: reward={reward}, actions={len(actions)}")
        return {
            "status": "sent",
            "reward": reward,
            "action_count": len(actions),
            "sona_response": result,
        }

    except Exception as exc:
        logger.error(f"Failed to send SONA trajectory: {exc}")
        raise


@app.task(
    bind=True,
    base=CallbackTask,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2},
    retry_backoff=True,
    acks_late=True,
)
def train_gnn_task(
    self,
    interactions: List[Dict[str, Any]],
    training_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Send query-result interaction data to RuVector GNN for graph learning.

    Background task that periodically sends accumulated query-result
    interaction data so RuVector's Graph Neural Network can learn from
    user search patterns and improve retrieval recall over time
    (+12.4% recall after 10K queries).

    Args:
        interactions: List of interaction dicts
                      e.g. [{"query": "...", "doc_id": "...", "relevance": 0.9}, ...]
        training_metadata: Optional metadata about the training batch

    Returns:
        Dict with GNN training response
    """
    import os

    try:
        self.update_state(state="PROGRESS", meta={"status": "training_gnn"})

        ruvector_url = os.environ.get("RUVECTOR_URL", "http://localhost:6333")

        # Use synchronous HTTP for Celery worker context
        import httpx

        with httpx.Client(base_url=ruvector_url, timeout=60.0) as client:
            response = client.post(
                "/gnn/train",
                json={
                    "interactions": interactions,
                    "metadata": training_metadata or {},
                },
            )
            response.raise_for_status()
            result = response.json()

        logger.info(f"GNN training batch sent: {len(interactions)} interactions")
        return {
            "status": "trained",
            "interaction_count": len(interactions),
            "gnn_response": result,
        }

    except Exception as exc:
        logger.error(f"Failed to train GNN: {exc}")
        raise


@app.task(bind=True, base=CallbackTask)
def boris_batch_vectorize_task(
    self,
    webset_id: str,
    batch_size: int = 100,
) -> Dict[str, Any]:
    """
    Boris-style parallel batch vectorization for webset items.

    Uses Boris orchestration patterns with musical cadence coordination
    (4/4 rhythm) for bulk insert/search cycles. Processes webset items
    in coordinated batches for optimal throughput.

    Args:
        webset_id: Webset ID to vectorize
        batch_size: Number of items per batch

    Returns:
        Dict with vectorization summary
    """
    import os

    try:
        self.update_state(state="PROGRESS", meta={"status": "loading_items", "webset_id": webset_id})

        # Load items from database
        with _get_db_connection() as conn:
            cur = conn.execute(
                "SELECT id, url, title, content FROM webset_items WHERE webset_id=? AND content IS NOT NULL",
                (webset_id,)
            )
            items = cur.fetchall()

        if not items:
            return {"webset_id": webset_id, "status": "no_items", "vectorized": 0}

        ruvector_url = os.environ.get("RUVECTOR_URL", "http://localhost:6333")
        import httpx

        total_vectorized = 0
        total_batches = (len(items) + batch_size - 1) // batch_size
        errors = []

        # Process in coordinated batches (Boris 4/4 rhythm)
        for batch_idx in range(total_batches):
            start = batch_idx * batch_size
            end = min(start + batch_size, len(items))
            batch = items[start:end]

            self.update_state(
                state="PROGRESS",
                meta={
                    "status": "vectorizing",
                    "batch": batch_idx + 1,
                    "total_batches": total_batches,
                    "vectorized": total_vectorized,
                }
            )

            # Prepare batch documents
            documents = []
            for item_id, url, title, content in batch:
                documents.append({
                    "doc_id": item_id,
                    "text": content,
                    "metadata": {
                        "url": url,
                        "title": title or "",
                        "webset_id": webset_id,
                    },
                })

            # Send batch to RuVector
            try:
                with httpx.Client(base_url=ruvector_url, timeout=120.0) as client:
                    response = client.post(
                        "/documents/bulk",
                        json={"documents": documents},
                    )
                    response.raise_for_status()

                total_vectorized += len(batch)
            except Exception as exc:
                error_msg = f"Batch {batch_idx + 1} failed: {exc}"
                logger.error(error_msg)
                errors.append(error_msg)

        logger.info(
            f"Boris batch vectorization completed for webset {webset_id}: "
            f"{total_vectorized}/{len(items)} items vectorized"
        )

        return {
            "webset_id": webset_id,
            "total_items": len(items),
            "vectorized": total_vectorized,
            "batches": total_batches,
            "batch_size": batch_size,
            "errors": errors,
        }

    except Exception as exc:
        logger.error(f"Boris batch vectorization failed for webset {webset_id}: {exc}")
        raise
