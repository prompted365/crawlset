"""
Celery application configuration for distributed task processing.

Provides:
- Redis backend for task queue and results
- Priority queues: realtime, batch, background
- Task routing based on priority
- Retry and timeout configurations
"""

from __future__ import annotations
import os
from celery import Celery
from kombu import Queue, Exchange

# Environment variables
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

# Create Celery app instance
app = Celery(
    "intelligence_pipeline",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["src.queue.tasks"],
)

# Celery configuration
app.conf.update(
    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Result backend settings
    result_backend=CELERY_RESULT_BACKEND,
    result_expires=3600 * 24,  # 24 hours
    result_extended=True,

    # Task execution settings
    task_acks_late=True,  # Acknowledge after task completes
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,  # Only fetch one task at a time for long-running tasks

    # Broker settings
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,

    # Task time limits (in seconds)
    task_time_limit=3600,  # Hard limit: 1 hour
    task_soft_time_limit=3300,  # Soft limit: 55 minutes

    # Priority queues configuration
    task_default_queue="batch",
    task_default_exchange="tasks",
    task_default_exchange_type="direct",
    task_default_routing_key="batch",

    # Define queues with priorities
    task_queues=(
        Queue(
            "realtime",
            Exchange("tasks"),
            routing_key="realtime",
            queue_arguments={"x-max-priority": 10},
        ),
        Queue(
            "batch",
            Exchange("tasks"),
            routing_key="batch",
            queue_arguments={"x-max-priority": 5},
        ),
        Queue(
            "background",
            Exchange("tasks"),
            routing_key="background",
            queue_arguments={"x-max-priority": 1},
        ),
    ),

    # Task routes - map task names to queues
    task_routes={
        "src.queue.tasks.extract_url_task": {"queue": "realtime", "routing_key": "realtime"},
        "src.queue.tasks.enrich_item_task": {"queue": "realtime", "routing_key": "realtime"},
        "src.queue.tasks.batch_extract_task": {"queue": "batch", "routing_key": "batch"},
        "src.queue.tasks.process_webset_task": {"queue": "batch", "routing_key": "batch"},
        "src.queue.tasks.run_monitor_task": {"queue": "background", "routing_key": "background"},
    },

    # Worker settings
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s",

    # Task tracking
    task_track_started=True,
    task_send_sent_event=True,
)


# Task annotations for specific behavior
app.conf.task_annotations = {
    "*": {
        "rate_limit": None,  # No rate limiting by default
        "time_limit": 3600,
        "soft_time_limit": 3300,
    },
    "src.queue.tasks.extract_url_task": {
        "rate_limit": "100/m",  # Max 100 per minute
        "time_limit": 300,  # 5 minutes
        "soft_time_limit": 270,
    },
    "src.queue.tasks.enrich_item_task": {
        "rate_limit": "50/m",
        "time_limit": 600,  # 10 minutes
        "soft_time_limit": 540,
    },
    "src.queue.tasks.batch_extract_task": {
        "time_limit": 3600,  # 1 hour
        "soft_time_limit": 3300,
    },
    "src.queue.tasks.process_webset_task": {
        "time_limit": 7200,  # 2 hours
        "soft_time_limit": 6900,
    },
    "src.queue.tasks.run_monitor_task": {
        "time_limit": 1800,  # 30 minutes
        "soft_time_limit": 1620,
    },
}


# Celery beat schedule (for periodic tasks)
app.conf.beat_schedule = {
    # Example: Clean up old results every day
    "cleanup-expired-results": {
        "task": "src.queue.tasks.cleanup_expired_results",
        "schedule": 86400.0,  # 24 hours
        "options": {"queue": "background"},
    },
}


if __name__ == "__main__":
    app.start()
