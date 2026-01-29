"""
Monitor behavior implementations for different types of webset monitoring.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Set
from abc import ABC, abstractmethod
from datetime import datetime
import logging

from ..websets.manager import WebsetManager, WebsetItem
from ..websets.search import SearchExecutor, SearchResult
from ..websets.deduplication import ContentDeduplicator
from ..crawler.browser import fetch_page
from ..parser.trafilatura_parser import parse_html
from ..ruvector.client import RuVectorClient

logger = logging.getLogger(__name__)


class BehaviorResult:
    """Result of a behavior execution."""

    def __init__(self):
        self.items_added = 0
        self.items_updated = 0
        self.items_skipped = 0
        self.errors: List[str] = []
        self.details: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items_added": self.items_added,
            "items_updated": self.items_updated,
            "items_skipped": self.items_skipped,
            "errors": self.errors,
            "details": self.details,
        }


class MonitorBehavior(ABC):
    """Base class for monitor behaviors."""

    def __init__(
        self,
        manager: WebsetManager,
        search_executor: Optional[SearchExecutor] = None,
        deduplicator: Optional[ContentDeduplicator] = None,
        ruvector_client: Optional[RuVectorClient] = None,
    ):
        self.manager = manager
        self.search_executor = search_executor or SearchExecutor()
        self.deduplicator = deduplicator or ContentDeduplicator()
        self.ruvector_client = ruvector_client or RuVectorClient(data_dir="./data/ruvector")

    @abstractmethod
    async def execute(
        self,
        webset_id: str,
        config: Dict[str, Any],
    ) -> BehaviorResult:
        """
        Execute the behavior.

        Args:
            webset_id: Webset ID
            config: Behavior configuration

        Returns:
            BehaviorResult with execution details
        """
        pass

    async def _get_existing_content_hashes(self, webset_id: str) -> Set[str]:
        """Get all existing content hashes for a webset."""
        items = await self.manager.get_items(webset_id, limit=10000)
        return {item.content_hash for item in items if item.content_hash}

    async def _store_to_ruvector(
        self,
        item: WebsetItem,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Store item content to RuVector."""
        if not item.content:
            return

        doc_metadata = metadata or {}
        doc_metadata.update({
            "url": item.url,
            "title": item.title or "",
            "webset_id": item.webset_id,
            "item_id": item.id,
        })

        try:
            await self.ruvector_client.insert_document(
                doc_id=item.id,
                text=item.content,
                metadata=doc_metadata,
            )

            # Update item with RuVector doc ID
            await self.manager.update_item(
                item_id=item.id,
                ruvector_doc_id=item.id,
            )
        except Exception as e:
            logger.error(f"Failed to store item {item.id} to RuVector: {e}")


class SearchBehavior(MonitorBehavior):
    """
    Search behavior: Run queries, dedupe, append new results.
    """

    async def execute(
        self,
        webset_id: str,
        config: Dict[str, Any],
    ) -> BehaviorResult:
        """
        Execute search behavior.

        Config options:
            - query: Search query string (required)
            - search_type: Type of search (ruvector, web)
            - top_k: Number of results to fetch
            - crawl_results: Whether to crawl result URLs
            - deduplicate: Whether to deduplicate results
            - store_to_ruvector: Whether to store results in RuVector
        """
        result = BehaviorResult()

        try:
            # Get webset
            webset = await self.manager.get_webset(webset_id)
            if not webset:
                result.errors.append(f"Webset {webset_id} not found")
                return result

            # Extract config
            query = config.get("query") or webset.search_query
            if not query:
                result.errors.append("No search query provided")
                return result

            search_type = config.get("search_type", "ruvector")
            top_k = config.get("top_k", 10)
            crawl_results = config.get("crawl_results", True)
            deduplicate = config.get("deduplicate", True)
            store_to_ruvector = config.get("store_to_ruvector", True)

            # Get existing content hashes for deduplication
            existing_hashes = await self._get_existing_content_hashes(webset_id) if deduplicate else set()

            # Execute search
            logger.info(f"Executing {search_type} search for webset {webset_id}: {query}")
            search_results = await self.search_executor.search_and_crawl(
                query=query,
                search_type=search_type,
                top_k=top_k,
                crawl_results=crawl_results,
                deduplicate=deduplicate,
                existing_content_hashes=existing_hashes,
            )

            result.details["search_results_count"] = len(search_results)

            # Add new items to webset
            for search_result in search_results:
                try:
                    # Check if URL already exists
                    existing_item = await self.manager.find_item_by_url(webset_id, search_result.url)
                    if existing_item:
                        result.items_skipped += 1
                        continue

                    # Add new item
                    item = await self.manager.add_item(
                        webset_id=webset_id,
                        url=search_result.url,
                        title=search_result.title,
                        content=search_result.content,
                        metadata=search_result.metadata,
                    )

                    if item:
                        result.items_added += 1

                        # Store to RuVector if requested
                        if store_to_ruvector and item.content:
                            await self._store_to_ruvector(item, search_result.metadata)

                except Exception as e:
                    error_msg = f"Failed to add item {search_result.url}: {e}"
                    logger.error(error_msg)
                    result.errors.append(error_msg)

            logger.info(f"Search behavior completed: {result.items_added} added, {result.items_skipped} skipped")

        except Exception as e:
            error_msg = f"Search behavior failed: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)

        return result


class RefreshBehavior(MonitorBehavior):
    """
    Refresh behavior: Re-crawl URLs, update enrichments.
    """

    async def execute(
        self,
        webset_id: str,
        config: Dict[str, Any],
    ) -> BehaviorResult:
        """
        Execute refresh behavior.

        Config options:
            - use_playwright: Whether to use Playwright for crawling
            - update_ruvector: Whether to update RuVector documents
            - run_enrichments: Whether to run enrichments
            - max_items: Maximum number of items to refresh (0 = all)
        """
        result = BehaviorResult()

        try:
            # Extract config
            use_playwright = config.get("use_playwright", False)
            update_ruvector = config.get("update_ruvector", True)
            run_enrichments = config.get("run_enrichments", True)
            max_items = config.get("max_items", 0)

            # Get items to refresh
            items = await self.manager.get_items(
                webset_id,
                limit=max_items if max_items > 0 else 10000,
            )

            result.details["items_to_refresh"] = len(items)

            # Refresh each item
            for item in items:
                try:
                    # Fetch and parse page
                    html = await fetch_page(item.url, use_playwright=use_playwright)
                    parsed = parse_html(item.url, html)

                    new_content = parsed.get("text", "")
                    new_title = parsed.get("title", item.title)

                    # Check if content changed
                    new_hash = self.deduplicator.compute_hash(new_content)
                    content_changed = (new_hash != item.content_hash)

                    if content_changed:
                        result.items_updated += 1

                        # Update item
                        await self.manager.update_item(
                            item_id=item.id,
                            title=new_title,
                            content=new_content,
                        )

                        # Update RuVector if requested
                        if update_ruvector:
                            updated_item = await self.manager.get_item(item.id)
                            if updated_item:
                                await self._store_to_ruvector(updated_item)

                        logger.info(f"Updated item {item.id}: content changed")
                    else:
                        result.items_skipped += 1

                    # Run enrichments if requested
                    if run_enrichments and content_changed:
                        # Enrichments will be run by the enrichment engine
                        pass

                except Exception as e:
                    error_msg = f"Failed to refresh item {item.id} ({item.url}): {e}"
                    logger.error(error_msg)
                    result.errors.append(error_msg)

            logger.info(f"Refresh behavior completed: {result.items_updated} updated, {result.items_skipped} unchanged")

        except Exception as e:
            error_msg = f"Refresh behavior failed: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)

        return result


class HybridBehavior(MonitorBehavior):
    """
    Hybrid behavior: Search + refresh combined.
    First runs search to find new items, then refreshes existing items.
    """

    async def execute(
        self,
        webset_id: str,
        config: Dict[str, Any],
    ) -> BehaviorResult:
        """
        Execute hybrid behavior.

        Config options:
            - All options from SearchBehavior and RefreshBehavior
            - search_config: Config dict for search phase
            - refresh_config: Config dict for refresh phase
        """
        result = BehaviorResult()

        try:
            # Extract configs
            search_config = config.get("search_config", {})
            refresh_config = config.get("refresh_config", {})

            # Phase 1: Search for new items
            logger.info(f"Hybrid behavior: Starting search phase for webset {webset_id}")
            search_behavior = SearchBehavior(
                manager=self.manager,
                search_executor=self.search_executor,
                deduplicator=self.deduplicator,
                ruvector_client=self.ruvector_client,
            )
            search_result = await search_behavior.execute(webset_id, search_config)

            result.items_added = search_result.items_added
            result.errors.extend(search_result.errors)
            result.details["search_phase"] = search_result.to_dict()

            # Phase 2: Refresh existing items
            logger.info(f"Hybrid behavior: Starting refresh phase for webset {webset_id}")
            refresh_behavior = RefreshBehavior(
                manager=self.manager,
                search_executor=self.search_executor,
                deduplicator=self.deduplicator,
                ruvector_client=self.ruvector_client,
            )
            refresh_result = await refresh_behavior.execute(webset_id, refresh_config)

            result.items_updated = refresh_result.items_updated
            result.items_skipped = refresh_result.items_skipped
            result.errors.extend(refresh_result.errors)
            result.details["refresh_phase"] = refresh_result.to_dict()

            logger.info(
                f"Hybrid behavior completed: "
                f"{result.items_added} added, "
                f"{result.items_updated} updated, "
                f"{result.items_skipped} skipped"
            )

        except Exception as e:
            error_msg = f"Hybrid behavior failed: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)

        return result


class BehaviorFactory:
    """Factory for creating behavior instances."""

    BEHAVIORS = {
        "search": SearchBehavior,
        "refresh": RefreshBehavior,
        "hybrid": HybridBehavior,
    }

    @classmethod
    def create(
        cls,
        behavior_type: str,
        manager: WebsetManager,
        search_executor: Optional[SearchExecutor] = None,
        deduplicator: Optional[ContentDeduplicator] = None,
        ruvector_client: Optional[RuVectorClient] = None,
    ) -> MonitorBehavior:
        """
        Create a behavior instance.

        Args:
            behavior_type: Type of behavior (search, refresh, hybrid)
            manager: WebsetManager instance
            search_executor: SearchExecutor instance
            deduplicator: ContentDeduplicator instance
            ruvector_client: RuVectorClient instance

        Returns:
            MonitorBehavior instance

        Raises:
            ValueError: If behavior type is unknown
        """
        behavior_class = cls.BEHAVIORS.get(behavior_type)
        if not behavior_class:
            raise ValueError(
                f"Unknown behavior type: {behavior_type}. "
                f"Available: {', '.join(cls.BEHAVIORS.keys())}"
            )

        return behavior_class(
            manager=manager,
            search_executor=search_executor,
            deduplicator=deduplicator,
            ruvector_client=ruvector_client,
        )
