"""
Celery worker configuration and health check utilities.

Provides:
- Worker startup and configuration
- Health check endpoints
- Worker monitoring and stats
- Resource management
- Graceful shutdown handling
"""

from __future__ import annotations
import logging
import os
import signal
import sys
import time
from typing import Any, Dict, Optional
import psutil
from celery import Celery
from celery.signals import (
    worker_ready,
    worker_shutdown,
    worker_process_init,
    task_prerun,
    task_postrun,
    task_failure,
)

from .celery_app import app

logger = logging.getLogger(__name__)

# Worker configuration
WORKER_CONCURRENCY = int(os.getenv("CELERY_WORKER_CONCURRENCY", "4"))
WORKER_MAX_TASKS_PER_CHILD = int(os.getenv("CELERY_WORKER_MAX_TASKS_PER_CHILD", "100"))
WORKER_MAX_MEMORY_PER_CHILD = int(os.getenv("CELERY_WORKER_MAX_MEMORY_MB", "512")) * 1024 * 1024  # Convert to bytes


class WorkerHealthCheck:
    """Worker health check and monitoring."""

    def __init__(self):
        self.start_time = time.time()
        self.task_count = 0
        self.task_failures = 0
        self.task_successes = 0
        self.current_task_id = None
        self.current_task_start = None

    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics."""
        process = psutil.Process()
        memory_info = process.memory_info()
        cpu_percent = process.cpu_percent(interval=0.1)

        uptime = time.time() - self.start_time

        stats = {
            "status": "healthy",
            "uptime_seconds": uptime,
            "tasks": {
                "total": self.task_count,
                "successes": self.task_successes,
                "failures": self.task_failures,
                "current_task_id": self.current_task_id,
                "current_task_duration": (
                    time.time() - self.current_task_start if self.current_task_start else None
                ),
            },
            "resources": {
                "memory_rss_mb": memory_info.rss / 1024 / 1024,
                "memory_percent": process.memory_percent(),
                "cpu_percent": cpu_percent,
                "num_threads": process.num_threads(),
            },
            "connections": {
                "open_files": len(process.open_files()),
                "num_connections": len(process.connections()),
            },
        }

        return stats

    def is_healthy(self) -> bool:
        """Check if worker is healthy."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()

            # Check memory usage
            if memory_info.rss > WORKER_MAX_MEMORY_PER_CHILD:
                logger.warning(
                    f"Worker memory usage ({memory_info.rss / 1024 / 1024:.2f}MB) "
                    f"exceeds limit ({WORKER_MAX_MEMORY_PER_CHILD / 1024 / 1024:.2f}MB)"
                )
                return False

            # Check if worker is responsive
            if self.current_task_start:
                task_duration = time.time() - self.current_task_start
                if task_duration > 3600:  # 1 hour
                    logger.warning(f"Task {self.current_task_id} running for {task_duration:.2f}s")
                    return False

            return True

        except Exception as exc:
            logger.error(f"Health check failed: {exc}")
            return False


# Global health check instance
health_check = WorkerHealthCheck()


# Signal handlers

@worker_ready.connect
def on_worker_ready(sender, **kwargs):
    """Called when worker is ready to accept tasks."""
    logger.info(f"Worker {sender} is ready")
    logger.info(f"Concurrency: {WORKER_CONCURRENCY}")
    logger.info(f"Max tasks per child: {WORKER_MAX_TASKS_PER_CHILD}")
    logger.info(f"Max memory per child: {WORKER_MAX_MEMORY_PER_CHILD / 1024 / 1024:.2f}MB")


@worker_shutdown.connect
def on_worker_shutdown(sender, **kwargs):
    """Called when worker is shutting down."""
    logger.info(f"Worker {sender} shutting down")
    stats = health_check.get_stats()
    logger.info(f"Final stats: {stats}")


@worker_process_init.connect
def on_worker_process_init(sender, **kwargs):
    """Called when worker process initializes."""
    logger.info(f"Worker process initialized: PID {os.getpid()}")


@task_prerun.connect
def on_task_prerun(sender, task_id, task, args, kwargs, **extra):
    """Called before task execution."""
    health_check.task_count += 1
    health_check.current_task_id = task_id
    health_check.current_task_start = time.time()
    logger.info(f"Starting task {task.name}[{task_id}]")


@task_postrun.connect
def on_task_postrun(sender, task_id, task, args, kwargs, retval, **extra):
    """Called after task execution."""
    duration = time.time() - health_check.current_task_start if health_check.current_task_start else 0
    health_check.task_successes += 1
    health_check.current_task_id = None
    health_check.current_task_start = None
    logger.info(f"Completed task {task.name}[{task_id}] in {duration:.2f}s")


@task_failure.connect
def on_task_failure(sender, task_id, exception, args, kwargs, traceback, einfo, **extra):
    """Called when task fails."""
    health_check.task_failures += 1
    health_check.current_task_id = None
    health_check.current_task_start = None
    logger.error(f"Task {sender.name}[{task_id}] failed: {exception}")


# Resource management functions

def check_memory_usage():
    """Check and log memory usage."""
    process = psutil.Process()
    memory_info = process.memory_info()
    memory_mb = memory_info.rss / 1024 / 1024
    logger.info(f"Worker memory usage: {memory_mb:.2f}MB")

    if memory_info.rss > WORKER_MAX_MEMORY_PER_CHILD:
        logger.warning(
            f"Memory usage ({memory_mb:.2f}MB) exceeds limit "
            f"({WORKER_MAX_MEMORY_PER_CHILD / 1024 / 1024:.2f}MB)"
        )
        return False
    return True


def cleanup_resources():
    """Clean up resources (close connections, clear caches)."""
    try:
        # Close database connections
        import sqlite3
        # SQLite connections are per-thread, will be closed automatically

        # Clear any caches
        import gc
        gc.collect()

        logger.info("Resources cleaned up")

    except Exception as exc:
        logger.error(f"Failed to clean up resources: {exc}")


# Worker startup functions

def start_worker(
    queues: Optional[list] = None,
    concurrency: Optional[int] = None,
    loglevel: str = "INFO",
    max_tasks_per_child: Optional[int] = None,
):
    """
    Start a Celery worker.

    Args:
        queues: List of queue names to consume from
        concurrency: Number of worker processes/threads
        loglevel: Logging level
        max_tasks_per_child: Max tasks per worker process before restart
    """
    queues = queues or ["realtime", "batch", "background"]
    concurrency = concurrency or WORKER_CONCURRENCY
    max_tasks_per_child = max_tasks_per_child or WORKER_MAX_TASKS_PER_CHILD

    # Configure worker arguments
    worker_args = [
        "worker",
        f"--loglevel={loglevel}",
        f"--concurrency={concurrency}",
        f"--max-tasks-per-child={max_tasks_per_child}",
        f"--queues={','.join(queues)}",
        "--pool=prefork",  # Use prefork pool for better isolation
    ]

    logger.info(f"Starting worker with queues: {queues}")
    logger.info(f"Concurrency: {concurrency}")
    logger.info(f"Max tasks per child: {max_tasks_per_child}")

    # Start worker
    app.worker_main(argv=worker_args)


def start_realtime_worker(loglevel: str = "INFO"):
    """Start a worker for realtime queue."""
    start_worker(queues=["realtime"], concurrency=4, loglevel=loglevel)


def start_batch_worker(loglevel: str = "INFO"):
    """Start a worker for batch queue."""
    start_worker(queues=["batch"], concurrency=2, loglevel=loglevel)


def start_background_worker(loglevel: str = "INFO"):
    """Start a worker for background queue."""
    start_worker(queues=["background"], concurrency=1, loglevel=loglevel)


# Health check API

def get_worker_health() -> Dict[str, Any]:
    """Get worker health status."""
    is_healthy = health_check.is_healthy()
    stats = health_check.get_stats()
    stats["status"] = "healthy" if is_healthy else "unhealthy"
    return stats


# CLI entry points

def main():
    """Main entry point for worker CLI."""
    import argparse

    parser = argparse.ArgumentParser(description="Intelligence Pipeline Celery Worker")
    parser.add_argument(
        "--queues",
        nargs="+",
        default=["realtime", "batch", "background"],
        help="Queues to consume from",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=WORKER_CONCURRENCY,
        help="Number of concurrent workers",
    )
    parser.add_argument(
        "--loglevel",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level",
    )
    parser.add_argument(
        "--max-tasks-per-child",
        type=int,
        default=WORKER_MAX_TASKS_PER_CHILD,
        help="Max tasks per child process",
    )
    parser.add_argument(
        "--worker-type",
        choices=["all", "realtime", "batch", "background"],
        default="all",
        help="Worker type (queue specialization)",
    )

    args = parser.parse_args()

    # Start appropriate worker
    if args.worker_type == "realtime":
        start_realtime_worker(loglevel=args.loglevel)
    elif args.worker_type == "batch":
        start_batch_worker(loglevel=args.loglevel)
    elif args.worker_type == "background":
        start_background_worker(loglevel=args.loglevel)
    else:
        start_worker(
            queues=args.queues,
            concurrency=args.concurrency,
            loglevel=args.loglevel,
            max_tasks_per_child=args.max_tasks_per_child,
        )


if __name__ == "__main__":
    main()
