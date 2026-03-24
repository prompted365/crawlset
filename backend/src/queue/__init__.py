"""
Queue module for distributed task processing.

Provides Celery-based task queue infrastructure with:
- Task definitions for extraction, enrichment, and monitoring
- Worker management and health checks
- Priority queues (realtime, batch, background)
"""

from .celery_app import app
# Tasks and workers are NOT eagerly imported here.
# Tasks are auto-discovered via celery_app include=["src.queue.tasks"].
# Import directly where needed to avoid pulling heavy deps into API startup.

__all__ = [
    "app",
]
