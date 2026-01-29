"""
Enrichment plugin system for extracting structured information from webset items.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Type
from abc import ABC, abstractmethod
import logging
from datetime import datetime
import importlib
import inspect

logger = logging.getLogger(__name__)


class EnrichmentResult:
    """Result of an enrichment operation."""

    def __init__(self, plugin_name: str):
        self.plugin_name = plugin_name
        self.success = False
        self.data: Dict[str, Any] = {}
        self.error: Optional[str] = None
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_name": self.plugin_name,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class EnrichmentPlugin(ABC):
    """Base class for enrichment plugins."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the plugin.

        Args:
            config: Plugin-specific configuration
        """
        self.config = config or {}
        self.name = self.__class__.__name__

    @abstractmethod
    async def enrich(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EnrichmentResult:
        """
        Enrich content with extracted information.

        Args:
            content: Text content to enrich
            metadata: Optional metadata about the content

        Returns:
            EnrichmentResult with extracted data
        """
        pass

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """
        Get the output schema for this plugin.

        Returns:
            JSON schema describing the enrichment output
        """
        pass

    def validate_input(self, content: str) -> bool:
        """
        Validate input content before enrichment.

        Args:
            content: Content to validate

        Returns:
            True if content is valid for this enrichment
        """
        return bool(content and content.strip())


class EnrichmentEngine:
    """
    Engine for managing and executing enrichment plugins.
    """

    def __init__(self):
        self.plugins: Dict[str, EnrichmentPlugin] = {}

    def register_plugin(
        self,
        plugin: EnrichmentPlugin,
        name: Optional[str] = None,
    ):
        """
        Register an enrichment plugin.

        Args:
            plugin: EnrichmentPlugin instance
            name: Optional plugin name (defaults to class name)
        """
        plugin_name = name or plugin.name
        self.plugins[plugin_name] = plugin
        logger.info(f"Registered enrichment plugin: {plugin_name}")

    def unregister_plugin(self, name: str):
        """
        Unregister an enrichment plugin.

        Args:
            name: Plugin name
        """
        if name in self.plugins:
            del self.plugins[name]
            logger.info(f"Unregistered enrichment plugin: {name}")

    def get_plugin(self, name: str) -> Optional[EnrichmentPlugin]:
        """Get a plugin by name."""
        return self.plugins.get(name)

    def list_plugins(self) -> List[Dict[str, Any]]:
        """
        List all registered plugins.

        Returns:
            List of plugin info dicts
        """
        return [
            {
                "name": name,
                "schema": plugin.get_schema(),
            }
            for name, plugin in self.plugins.items()
        ]

    async def enrich(
        self,
        content: str,
        plugin_names: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, EnrichmentResult]:
        """
        Run enrichments on content.

        Args:
            content: Text content to enrich
            plugin_names: Optional list of plugin names to run (defaults to all)
            metadata: Optional metadata about the content

        Returns:
            Dict mapping plugin names to enrichment results
        """
        plugins_to_run = plugin_names or list(self.plugins.keys())

        results = {}
        for plugin_name in plugins_to_run:
            plugin = self.plugins.get(plugin_name)
            if not plugin:
                logger.warning(f"Plugin {plugin_name} not found, skipping")
                continue

            try:
                # Validate input
                if not plugin.validate_input(content):
                    logger.warning(f"Invalid input for plugin {plugin_name}, skipping")
                    result = EnrichmentResult(plugin_name)
                    result.error = "Invalid input"
                    results[plugin_name] = result
                    continue

                # Run enrichment
                logger.info(f"Running enrichment: {plugin_name}")
                result = await plugin.enrich(content, metadata)
                results[plugin_name] = result

                if result.success:
                    logger.info(f"Enrichment {plugin_name} completed successfully")
                else:
                    logger.warning(f"Enrichment {plugin_name} failed: {result.error}")

            except Exception as e:
                logger.error(f"Error running enrichment {plugin_name}: {e}")
                result = EnrichmentResult(plugin_name)
                result.error = str(e)
                results[plugin_name] = result

        return results

    async def enrich_batch(
        self,
        items: List[Dict[str, Any]],
        plugin_names: Optional[List[str]] = None,
        content_key: str = "content",
    ) -> List[Dict[str, Any]]:
        """
        Run enrichments on a batch of items.

        Args:
            items: List of items with content
            plugin_names: Optional list of plugin names to run
            content_key: Key for content field in items

        Returns:
            List of items with enrichments added
        """
        enriched_items = []

        for item in items:
            content = item.get(content_key, "")
            if not content:
                enriched_items.append(item)
                continue

            # Run enrichments
            results = await self.enrich(
                content=content,
                plugin_names=plugin_names,
                metadata=item.get("metadata"),
            )

            # Add enrichments to item
            item["enrichments"] = {
                name: result.to_dict()
                for name, result in results.items()
            }

            enriched_items.append(item)

        return enriched_items

    def auto_discover_plugins(self, package_path: str = "enrichments.plugins"):
        """
        Auto-discover and register plugins from a package.

        Args:
            package_path: Python package path to search for plugins
        """
        try:
            package = importlib.import_module(package_path)
            package_dir = package.__path__[0]

            # Import all modules in the package
            import os
            for filename in os.listdir(package_dir):
                if filename.endswith(".py") and not filename.startswith("_"):
                    module_name = filename[:-3]
                    module = importlib.import_module(f"{package_path}.{module_name}")

                    # Find EnrichmentPlugin subclasses
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if (
                            issubclass(obj, EnrichmentPlugin)
                            and obj != EnrichmentPlugin
                            and obj.__module__ == module.__name__
                        ):
                            # Instantiate and register
                            plugin = obj()
                            self.register_plugin(plugin)
                            logger.info(f"Auto-discovered plugin: {name}")

        except Exception as e:
            logger.error(f"Failed to auto-discover plugins: {e}")


class EnrichmentPipeline:
    """
    Pipeline for running multiple enrichments in sequence.
    """

    def __init__(self, engine: EnrichmentEngine):
        self.engine = engine
        self.stages: List[Dict[str, Any]] = []

    def add_stage(
        self,
        plugin_names: List[str],
        condition: Optional[callable] = None,
    ):
        """
        Add a stage to the pipeline.

        Args:
            plugin_names: List of plugin names to run in this stage
            condition: Optional function to determine if stage should run
        """
        self.stages.append({
            "plugin_names": plugin_names,
            "condition": condition,
        })

    async def run(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run the pipeline on content.

        Args:
            content: Text content to process
            metadata: Optional metadata

        Returns:
            Dict with all enrichment results
        """
        all_results = {}

        for i, stage in enumerate(self.stages):
            plugin_names = stage["plugin_names"]
            condition = stage["condition"]

            # Check condition
            if condition and not condition(content, metadata, all_results):
                logger.info(f"Skipping pipeline stage {i}: condition not met")
                continue

            # Run stage
            logger.info(f"Running pipeline stage {i}: {plugin_names}")
            results = await self.engine.enrich(
                content=content,
                plugin_names=plugin_names,
                metadata=metadata,
            )

            # Merge results
            all_results.update(results)

        return all_results


class EnrichmentCache:
    """
    Simple in-memory cache for enrichment results.
    """

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: Dict[str, Dict[str, Any]] = {}

    def _make_key(self, content: str, plugin_name: str) -> str:
        """Create cache key from content and plugin name."""
        import hashlib
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"{plugin_name}:{content_hash}"

    def get(self, content: str, plugin_name: str) -> Optional[EnrichmentResult]:
        """Get cached result."""
        key = self._make_key(content, plugin_name)
        cached = self.cache.get(key)
        if cached:
            result = EnrichmentResult(plugin_name)
            result.success = cached["success"]
            result.data = cached["data"]
            result.error = cached["error"]
            result.timestamp = cached["timestamp"]
            return result
        return None

    def set(self, content: str, plugin_name: str, result: EnrichmentResult):
        """Set cached result."""
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]

        key = self._make_key(content, plugin_name)
        self.cache[key] = result.to_dict()

    def clear(self):
        """Clear cache."""
        self.cache.clear()


class CachedEnrichmentEngine(EnrichmentEngine):
    """EnrichmentEngine with result caching."""

    def __init__(self, cache_size: int = 1000):
        super().__init__()
        self.cache = EnrichmentCache(max_size=cache_size)

    async def enrich(
        self,
        content: str,
        plugin_names: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, EnrichmentResult]:
        """Run enrichments with caching."""
        plugins_to_run = plugin_names or list(self.plugins.keys())

        results = {}
        for plugin_name in plugins_to_run:
            # Check cache first
            cached_result = self.cache.get(content, plugin_name)
            if cached_result:
                logger.info(f"Using cached result for {plugin_name}")
                results[plugin_name] = cached_result
                continue

            # Run enrichment
            plugin = self.plugins.get(plugin_name)
            if not plugin:
                continue

            try:
                result = await plugin.enrich(content, metadata)
                results[plugin_name] = result

                # Cache result
                if result.success:
                    self.cache.set(content, plugin_name, result)

            except Exception as e:
                logger.error(f"Error running enrichment {plugin_name}: {e}")
                result = EnrichmentResult(plugin_name)
                result.error = str(e)
                results[plugin_name] = result

        return results
