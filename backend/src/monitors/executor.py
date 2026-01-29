"""
Monitor execution logic with comprehensive error handling and retry mechanisms.
"""
from __future__ import annotations
from typing import Optional, Dict, Any
import logging
from datetime import datetime
import traceback
import json

from .behaviors import BehaviorFactory, BehaviorResult
from ..websets.manager import WebsetManager
from ..websets.search import SearchExecutor
from ..websets.deduplication import ContentDeduplicator
from ..ruvector.client import RuVectorClient

logger = logging.getLogger(__name__)


class ExecutionError(Exception):
    """Custom exception for monitor execution errors."""
    pass


class MonitorExecutor:
    """
    Executes monitor jobs with error handling and logging.
    """

    def __init__(
        self,
        db_url: str = "sqlite+aiosqlite:///./data/websets.db",
        ruvector_data_dir: str = "./data/ruvector",
    ):
        """
        Initialize the executor.

        Args:
            db_url: Database URL for webset manager
            ruvector_data_dir: Data directory for RuVector
        """
        self.db_url = db_url
        self.ruvector_data_dir = ruvector_data_dir

        # Initialize components
        self.manager = WebsetManager(db_url)
        self.search_executor = SearchExecutor(
            ruvector_client=RuVectorClient(data_dir=ruvector_data_dir)
        )
        self.deduplicator = ContentDeduplicator()
        self.ruvector_client = RuVectorClient(data_dir=ruvector_data_dir)

    async def execute_monitor(
        self,
        monitor_id: str,
        force: bool = False,
    ) -> BehaviorResult:
        """
        Execute a monitor job.

        Args:
            monitor_id: Monitor ID
            force: Force execution even if monitor is disabled

        Returns:
            BehaviorResult with execution details

        Raises:
            ExecutionError: If execution fails
        """
        logger.info(f"Starting execution for monitor {monitor_id}")

        # Initialize database
        await self.manager.init_db()

        # Get monitor
        monitor = await self.manager.get_monitor(monitor_id)
        if not monitor:
            error_msg = f"Monitor {monitor_id} not found"
            logger.error(error_msg)
            raise ExecutionError(error_msg)

        # Check if monitor is enabled
        if monitor.status != "enabled" and not force:
            error_msg = f"Monitor {monitor_id} is not enabled (status: {monitor.status})"
            logger.warning(error_msg)
            raise ExecutionError(error_msg)

        # Record run start
        run = await self.manager.record_monitor_run(
            monitor_id=monitor_id,
            status="running",
        )

        try:
            # Parse behavior config
            behavior_config = {}
            if monitor.behavior_config:
                try:
                    behavior_config = json.loads(monitor.behavior_config)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse behavior config: {e}")

            # Create behavior
            behavior = BehaviorFactory.create(
                behavior_type=monitor.behavior_type,
                manager=self.manager,
                search_executor=self.search_executor,
                deduplicator=self.deduplicator,
                ruvector_client=self.ruvector_client,
            )

            # Execute behavior
            logger.info(f"Executing {monitor.behavior_type} behavior for monitor {monitor_id}")
            result = await behavior.execute(
                webset_id=monitor.webset_id,
                config=behavior_config,
            )

            # Update run record
            await self.manager.record_monitor_run(
                monitor_id=monitor_id,
                status="completed" if not result.errors else "failed",
                items_added=result.items_added,
                items_updated=result.items_updated,
                error_message="; ".join(result.errors) if result.errors else None,
            )

            logger.info(
                f"Monitor {monitor_id} execution completed: "
                f"{result.items_added} added, {result.items_updated} updated, "
                f"{len(result.errors)} errors"
            )

            return result

        except Exception as e:
            # Log full traceback
            error_msg = f"Monitor {monitor_id} execution failed: {e}"
            error_trace = traceback.format_exc()
            logger.error(f"{error_msg}\n{error_trace}")

            # Record failure
            await self.manager.record_monitor_run(
                monitor_id=monitor_id,
                status="failed",
                error_message=f"{error_msg}\n{error_trace}",
            )

            # Update monitor status to error
            await self.manager.update_monitor(
                monitor_id=monitor_id,
                status="error",
            )

            raise ExecutionError(error_msg) from e

    async def execute_webset(
        self,
        webset_id: str,
        behavior_type: str = "refresh",
        behavior_config: Optional[Dict[str, Any]] = None,
    ) -> BehaviorResult:
        """
        Execute a one-time behavior for a webset (without monitor).

        Args:
            webset_id: Webset ID
            behavior_type: Type of behavior to execute
            behavior_config: Behavior configuration

        Returns:
            BehaviorResult with execution details
        """
        logger.info(f"Starting one-time execution for webset {webset_id}")

        # Initialize database
        await self.manager.init_db()

        # Get webset
        webset = await self.manager.get_webset(webset_id)
        if not webset:
            error_msg = f"Webset {webset_id} not found"
            logger.error(error_msg)
            raise ExecutionError(error_msg)

        try:
            # Create behavior
            behavior = BehaviorFactory.create(
                behavior_type=behavior_type,
                manager=self.manager,
                search_executor=self.search_executor,
                deduplicator=self.deduplicator,
                ruvector_client=self.ruvector_client,
            )

            # Execute behavior
            logger.info(f"Executing {behavior_type} behavior for webset {webset_id}")
            result = await behavior.execute(
                webset_id=webset_id,
                config=behavior_config or {},
            )

            logger.info(
                f"Webset {webset_id} execution completed: "
                f"{result.items_added} added, {result.items_updated} updated, "
                f"{len(result.errors)} errors"
            )

            return result

        except Exception as e:
            error_msg = f"Webset {webset_id} execution failed: {e}"
            error_trace = traceback.format_exc()
            logger.error(f"{error_msg}\n{error_trace}")

            raise ExecutionError(error_msg) from e

    async def get_monitor_status(self, monitor_id: str) -> Dict[str, Any]:
        """
        Get the current status of a monitor.

        Args:
            monitor_id: Monitor ID

        Returns:
            Dict with monitor status and recent runs
        """
        await self.manager.init_db()

        monitor = await self.manager.get_monitor(monitor_id)
        if not monitor:
            return {"error": f"Monitor {monitor_id} not found"}

        # Get recent runs
        runs = await self.manager.get_monitor_runs(monitor_id, limit=10)

        return {
            "monitor": monitor.to_dict(),
            "recent_runs": [run.to_dict() for run in runs],
            "total_runs": len(runs),
        }

    async def retry_failed_run(self, monitor_id: str) -> BehaviorResult:
        """
        Retry a monitor that failed in its last execution.

        Args:
            monitor_id: Monitor ID

        Returns:
            BehaviorResult with execution details
        """
        logger.info(f"Retrying failed monitor {monitor_id}")

        # Get monitor status
        status = await self.get_monitor_status(monitor_id)
        if "error" in status:
            raise ExecutionError(status["error"])

        monitor = status["monitor"]
        recent_runs = status["recent_runs"]

        # Check if last run failed
        if not recent_runs or recent_runs[0]["status"] != "failed":
            raise ExecutionError(f"Monitor {monitor_id} did not fail in last run")

        # Re-enable monitor if it's in error state
        if monitor["status"] == "error":
            await self.manager.update_monitor(
                monitor_id=monitor_id,
                status="enabled",
            )

        # Execute monitor
        return await self.execute_monitor(monitor_id, force=True)

    async def test_monitor_config(
        self,
        behavior_type: str,
        behavior_config: Dict[str, Any],
        webset_id: str,
    ) -> Dict[str, Any]:
        """
        Test a monitor configuration without persisting results.

        Args:
            behavior_type: Type of behavior
            behavior_config: Behavior configuration
            webset_id: Webset ID to test with

        Returns:
            Dict with test results and validation info
        """
        logger.info(f"Testing {behavior_type} behavior configuration")

        try:
            # Initialize database
            await self.manager.init_db()

            # Validate webset exists
            webset = await self.manager.get_webset(webset_id)
            if not webset:
                return {
                    "valid": False,
                    "error": f"Webset {webset_id} not found",
                }

            # Validate behavior type
            try:
                behavior = BehaviorFactory.create(
                    behavior_type=behavior_type,
                    manager=self.manager,
                    search_executor=self.search_executor,
                    deduplicator=self.deduplicator,
                    ruvector_client=self.ruvector_client,
                )
            except ValueError as e:
                return {
                    "valid": False,
                    "error": str(e),
                }

            # Validate config
            # TODO: Add schema validation for behavior configs

            return {
                "valid": True,
                "behavior_type": behavior_type,
                "webset_id": webset_id,
                "config": behavior_config,
            }

        except Exception as e:
            logger.error(f"Config test failed: {e}")
            return {
                "valid": False,
                "error": str(e),
            }
