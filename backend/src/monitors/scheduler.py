"""
Enhanced APScheduler setup with job persistence, timezone support, and monitor execution.
"""
from __future__ import annotations
from typing import Optional
from pathlib import Path
import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.executors.pool import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class MonitorScheduler:
    """
    Enhanced scheduler with job persistence, timezone support, and monitor execution.
    """

    def __init__(
        self,
        db_url: str = "sqlite:///./data/scheduler.db",
        manager_db_url: str = "sqlite+aiosqlite:///./data/websets.db",
        timezone: str = "UTC",
        use_async: bool = True,
    ):
        """
        Initialize the scheduler.

        Args:
            db_url: Database URL for job persistence (SQLAlchemy format)
            manager_db_url: Database URL for webset manager
            timezone: Default timezone for jobs
            use_async: Whether to use AsyncIOScheduler (True) or BackgroundScheduler (False)
        """
        self.db_url = db_url
        self.manager_db_url = manager_db_url
        self.timezone = timezone
        self.use_async = use_async

        # Configure job stores
        jobstores = {
            "default": SQLAlchemyJobStore(url=db_url)
        }

        # Configure executors
        executors = {
            "default": AsyncIOExecutor() if use_async else ThreadPoolExecutor(max_workers=10),
            "threadpool": ThreadPoolExecutor(max_workers=5),
        }

        # Job defaults
        job_defaults = {
            "coalesce": True,  # Combine missed runs
            "max_instances": 1,  # Only one instance of a job at a time
            "misfire_grace_time": 300,  # 5 minutes grace period for misfires
        }

        # Create scheduler
        if use_async:
            self.scheduler = AsyncIOScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone=timezone,
            )
        else:
            self.scheduler = BackgroundScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone=timezone,
            )

        self._is_running = False

    async def initialize(self):
        """Initialize the scheduler and load existing monitors."""
        from .executor import MonitorExecutor
        from ..websets.manager import WebsetManager

        # Initialize database
        manager = WebsetManager(self.manager_db_url)
        await manager.init_db()

        # Load existing enabled monitors
        monitors = await manager.list_monitors(status="enabled")

        for monitor in monitors:
            try:
                await self.add_monitor_job(
                    monitor_id=monitor.id,
                    cron_expression=monitor.cron_expression,
                    timezone=monitor.timezone,
                )
                logger.info(f"Loaded monitor job: {monitor.id}")
            except Exception as e:
                logger.error(f"Failed to load monitor {monitor.id}: {e}")

    async def add_monitor_job(
        self,
        monitor_id: str,
        cron_expression: str,
        timezone: Optional[str] = None,
    ):
        """
        Add a monitor job to the scheduler.

        Args:
            monitor_id: Monitor ID
            cron_expression: Cron expression for scheduling
            timezone: Timezone for the job
        """
        from .executor import MonitorExecutor

        tz = timezone or self.timezone

        try:
            # Parse cron expression
            trigger = CronTrigger.from_crontab(cron_expression, timezone=tz)

            # Create executor
            executor = MonitorExecutor(db_url=self.manager_db_url)

            # Add job
            if self.use_async:
                self.scheduler.add_job(
                    executor.execute_monitor,
                    trigger=trigger,
                    id=monitor_id,
                    args=[monitor_id],
                    replace_existing=True,
                )
            else:
                # For BackgroundScheduler, wrap async function
                def sync_wrapper(mid):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(executor.execute_monitor(mid))
                    finally:
                        loop.close()

                self.scheduler.add_job(
                    sync_wrapper,
                    trigger=trigger,
                    id=monitor_id,
                    args=[monitor_id],
                    replace_existing=True,
                )

            logger.info(f"Added monitor job {monitor_id} with cron: {cron_expression}")

        except Exception as e:
            logger.error(f"Failed to add monitor job {monitor_id}: {e}")
            raise

    async def remove_monitor_job(self, monitor_id: str):
        """
        Remove a monitor job from the scheduler.

        Args:
            monitor_id: Monitor ID
        """
        try:
            self.scheduler.remove_job(monitor_id)
            logger.info(f"Removed monitor job: {monitor_id}")
        except Exception as e:
            logger.error(f"Failed to remove monitor job {monitor_id}: {e}")

    async def pause_monitor_job(self, monitor_id: str):
        """Pause a monitor job."""
        try:
            self.scheduler.pause_job(monitor_id)
            logger.info(f"Paused monitor job: {monitor_id}")
        except Exception as e:
            logger.error(f"Failed to pause monitor job {monitor_id}: {e}")

    async def resume_monitor_job(self, monitor_id: str):
        """Resume a paused monitor job."""
        try:
            self.scheduler.resume_job(monitor_id)
            logger.info(f"Resumed monitor job: {monitor_id}")
        except Exception as e:
            logger.error(f"Failed to resume monitor job {monitor_id}: {e}")

    def start(self):
        """Start the scheduler."""
        if not self._is_running:
            self.scheduler.start()
            self._is_running = True
            logger.info("Scheduler started")

    def shutdown(self, wait: bool = True):
        """
        Shutdown the scheduler.

        Args:
            wait: Whether to wait for running jobs to complete
        """
        if self._is_running:
            self.scheduler.shutdown(wait=wait)
            self._is_running = False
            logger.info("Scheduler shutdown")

    def get_jobs(self):
        """Get all scheduled jobs."""
        return self.scheduler.get_jobs()

    def get_job(self, job_id: str):
        """Get a specific job by ID."""
        return self.scheduler.get_job(job_id)


# Backward compatibility: simple start function
async def start_scheduler(
    db_url: str = "sqlite:///./data/scheduler.db",
    manager_db_url: str = "sqlite+aiosqlite:///./data/websets.db",
) -> MonitorScheduler:
    """
    Start the monitor scheduler with job persistence.

    Args:
        db_url: Database URL for job persistence
        manager_db_url: Database URL for webset manager

    Returns:
        Initialized and started MonitorScheduler
    """
    scheduler = MonitorScheduler(
        db_url=db_url,
        manager_db_url=manager_db_url,
        use_async=True,
    )

    await scheduler.initialize()
    scheduler.start()

    return scheduler
