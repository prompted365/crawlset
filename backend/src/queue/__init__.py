"""
Queue module for distributed task processing.

Provides Celery-based task queue infrastructure with:
- Task definitions for extraction, enrichment, and monitoring
- Worker management and health checks
- Priority queues (realtime, batch, background)
"""

from .celery_app import app
from .tasks import (
    extract_url_task,
    batch_extract_task,
    process_webset_task,
    run_monitor_task,
    enrich_item_task,
    cleanup_expired_results,
)
from .workers import (
    start_worker,
    start_realtime_worker,
    start_batch_worker,
    start_background_worker,
    get_worker_health,
)

__all__ = [
    # Celery app
    "app",
    # Tasks
    "extract_url_task",
    "batch_extract_task",
    "process_webset_task",
    "run_monitor_task",
    "enrich_item_task",
    "cleanup_expired_results",
    # Workers
    "start_worker",
    "start_realtime_worker",
    "start_batch_worker",
    "start_background_worker",
    "get_worker_health",
]
