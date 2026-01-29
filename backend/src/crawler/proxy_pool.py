"""
Rotating proxy pool manager with health checking, automatic rotation, and rate limiting.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


class ProxyProtocol(str, Enum):
    """Supported proxy protocols."""
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


@dataclass
class ProxyConfig:
    """Proxy configuration."""
    url: str  # Format: protocol://host:port or protocol://user:pass@host:port
    protocol: ProxyProtocol = ProxyProtocol.HTTP
    username: Optional[str] = None
    password: Optional[str] = None
    max_concurrent: int = 5
    rate_limit_per_second: float = 1.0
    timeout: float = 10.0
    priority: int = 0  # Higher priority proxies are preferred
    tags: Set[str] = field(default_factory=set)  # For categorization (e.g., "residential", "datacenter")

    def __post_init__(self):
        # Parse URL if username/password not provided
        if not self.username or not self.password:
            parsed = urlparse(self.url)
            if parsed.username:
                self.username = parsed.username
            if parsed.password:
                self.password = parsed.password

    def to_dict(self) -> Dict[str, str]:
        """Convert to Playwright/httpx proxy format."""
        proxy_dict = {"server": self.url}
        if self.username:
            proxy_dict["username"] = self.username
        if self.password:
            proxy_dict["password"] = self.password
        return proxy_dict

    def to_httpx_proxies(self) -> Dict[str, str]:
        """Convert to httpx proxies format."""
        if self.username and self.password:
            parsed = urlparse(self.url)
            auth_url = f"{parsed.scheme}://{self.username}:{self.password}@{parsed.netloc}"
            return {"http://": auth_url, "https://": auth_url}
        return {"http://": self.url, "https://": self.url}


@dataclass
class ProxyStats:
    """Statistics for a proxy."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time_ms: float = 0.0
    last_used: float = 0.0
    last_health_check: float = 0.0
    consecutive_failures: int = 0
    is_healthy: bool = True
    current_concurrent: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    @property
    def average_response_time_ms(self) -> float:
        """Calculate average response time."""
        if self.successful_requests == 0:
            return 0.0
        return self.total_response_time_ms / self.successful_requests


class ProxyPool:
    """
    Rotating proxy pool manager with:
    - Health checking (periodic and on-demand)
    - Automatic rotation based on failure rate
    - Rate limiting per proxy
    - Concurrent request limiting
    - Priority-based selection
    """

    def __init__(
        self,
        proxies: Optional[List[ProxyConfig]] = None,
        health_check_interval: float = 300.0,  # 5 minutes
        health_check_url: str = "https://httpbin.org/ip",
        max_consecutive_failures: int = 3,
        min_success_rate: float = 0.5,
        rotation_strategy: str = "round-robin",  # "round-robin", "least-used", "fastest", "priority"
    ):
        self.proxies: Dict[str, ProxyConfig] = {}
        self.stats: Dict[str, ProxyStats] = {}
        self.health_check_interval = health_check_interval
        self.health_check_url = health_check_url
        self.max_consecutive_failures = max_consecutive_failures
        self.min_success_rate = min_success_rate
        self.rotation_strategy = rotation_strategy

        self._current_index = 0
        self._locks: Dict[str, asyncio.Semaphore] = {}
        self._rate_limiters: Dict[str, asyncio.Semaphore] = {}
        self._last_request_times: Dict[str, float] = {}
        self._health_check_task: Optional[asyncio.Task] = None
        self._running = False

        # Add initial proxies
        if proxies:
            for proxy in proxies:
                self.add_proxy(proxy)

    def add_proxy(self, proxy: ProxyConfig):
        """Add a proxy to the pool."""
        proxy_id = proxy.url
        self.proxies[proxy_id] = proxy
        self.stats[proxy_id] = ProxyStats()
        self._locks[proxy_id] = asyncio.Semaphore(proxy.max_concurrent)
        self._rate_limiters[proxy_id] = asyncio.Semaphore(1)
        self._last_request_times[proxy_id] = 0.0
        logger.info(f"Added proxy to pool: {proxy_id}")

    def remove_proxy(self, proxy_url: str):
        """Remove a proxy from the pool."""
        if proxy_url in self.proxies:
            del self.proxies[proxy_url]
            del self.stats[proxy_url]
            del self._locks[proxy_url]
            del self._rate_limiters[proxy_url]
            del self._last_request_times[proxy_url]
            logger.info(f"Removed proxy from pool: {proxy_url}")

    def get_proxy_stats(self, proxy_url: str) -> Optional[ProxyStats]:
        """Get statistics for a specific proxy."""
        return self.stats.get(proxy_url)

    def get_all_stats(self) -> Dict[str, ProxyStats]:
        """Get statistics for all proxies."""
        return self.stats.copy()

    async def start(self):
        """Start the proxy pool and health checking."""
        if self._running:
            return
        self._running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Proxy pool started")

    async def stop(self):
        """Stop the proxy pool."""
        self._running = False
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        logger.info("Proxy pool stopped")

    async def _health_check_loop(self):
        """Periodically check proxy health."""
        while self._running:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self.check_all_proxies_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")

    async def check_proxy_health(self, proxy_url: str) -> bool:
        """
        Check if a proxy is healthy by making a test request.

        Returns:
            True if proxy is healthy, False otherwise
        """
        proxy = self.proxies.get(proxy_url)
        if not proxy:
            return False

        stats = self.stats[proxy_url]
        start_time = time.time()

        try:
            async with httpx.AsyncClient(
                proxies=proxy.to_httpx_proxies(),
                timeout=proxy.timeout
            ) as client:
                response = await client.get(self.health_check_url)
                response.raise_for_status()

            # Proxy is healthy
            stats.is_healthy = True
            stats.consecutive_failures = 0
            stats.last_health_check = time.time()
            response_time = (time.time() - start_time) * 1000
            logger.debug(f"Proxy {proxy_url} is healthy (response time: {response_time:.2f}ms)")
            return True

        except Exception as e:
            # Proxy is unhealthy
            stats.consecutive_failures += 1
            stats.last_health_check = time.time()

            # Mark as unhealthy if too many failures
            if stats.consecutive_failures >= self.max_consecutive_failures:
                stats.is_healthy = False
                logger.warning(f"Proxy {proxy_url} marked as unhealthy after {stats.consecutive_failures} failures")

            logger.debug(f"Proxy {proxy_url} health check failed: {e}")
            return False

    async def check_all_proxies_health(self):
        """Check health of all proxies concurrently."""
        tasks = [self.check_proxy_health(url) for url in self.proxies.keys()]
        await asyncio.gather(*tasks, return_exceptions=True)

    def _get_healthy_proxies(self) -> List[str]:
        """Get list of healthy proxy URLs."""
        healthy = []
        for url, stats in self.stats.items():
            if stats.is_healthy and stats.success_rate >= self.min_success_rate:
                healthy.append(url)
        return healthy

    def _select_proxy(self) -> Optional[str]:
        """Select a proxy based on the rotation strategy."""
        healthy_proxies = self._get_healthy_proxies()
        if not healthy_proxies:
            # Fall back to any proxy if none are healthy
            logger.warning("No healthy proxies available, using any proxy")
            healthy_proxies = list(self.proxies.keys())
            if not healthy_proxies:
                return None

        if self.rotation_strategy == "round-robin":
            # Round-robin selection
            self._current_index = (self._current_index + 1) % len(healthy_proxies)
            return healthy_proxies[self._current_index]

        elif self.rotation_strategy == "least-used":
            # Select proxy with fewest total requests
            return min(healthy_proxies, key=lambda url: self.stats[url].total_requests)

        elif self.rotation_strategy == "fastest":
            # Select proxy with lowest average response time
            return min(
                healthy_proxies,
                key=lambda url: self.stats[url].average_response_time_ms or float('inf')
            )

        elif self.rotation_strategy == "priority":
            # Select proxy with highest priority
            return max(healthy_proxies, key=lambda url: self.proxies[url].priority)

        else:
            # Default to round-robin
            return healthy_proxies[0]

    async def _wait_for_rate_limit(self, proxy_url: str):
        """Wait if rate limit would be exceeded."""
        proxy = self.proxies[proxy_url]
        last_request = self._last_request_times[proxy_url]
        min_interval = 1.0 / proxy.rate_limit_per_second

        time_since_last = time.time() - last_request
        if time_since_last < min_interval:
            wait_time = min_interval - time_since_last
            await asyncio.sleep(wait_time)

        self._last_request_times[proxy_url] = time.time()

    async def get_proxy(self) -> Optional[ProxyConfig]:
        """
        Get the next available proxy from the pool.
        This method handles rate limiting and concurrent request limiting.

        Returns:
            ProxyConfig or None if no proxies available
        """
        proxy_url = self._select_proxy()
        if not proxy_url:
            logger.warning("No proxies available in pool")
            return None

        # Wait for rate limit
        await self._wait_for_rate_limit(proxy_url)

        # Acquire concurrent request limit
        await self._locks[proxy_url].acquire()

        stats = self.stats[proxy_url]
        stats.current_concurrent += 1

        return self.proxies[proxy_url]

    def release_proxy(self, proxy_url: str):
        """Release a proxy back to the pool."""
        if proxy_url in self._locks:
            stats = self.stats[proxy_url]
            stats.current_concurrent -= 1
            self._locks[proxy_url].release()

    async def record_request(
        self,
        proxy_url: str,
        success: bool,
        response_time_ms: Optional[float] = None
    ):
        """Record the result of a request made through a proxy."""
        if proxy_url not in self.stats:
            return

        stats = self.stats[proxy_url]
        stats.total_requests += 1
        stats.last_used = time.time()

        if success:
            stats.successful_requests += 1
            stats.consecutive_failures = 0
            if response_time_ms:
                stats.total_response_time_ms += response_time_ms
        else:
            stats.failed_requests += 1
            stats.consecutive_failures += 1

            # Mark as unhealthy if too many consecutive failures
            if stats.consecutive_failures >= self.max_consecutive_failures:
                stats.is_healthy = False
                logger.warning(
                    f"Proxy {proxy_url} marked as unhealthy after "
                    f"{stats.consecutive_failures} consecutive failures"
                )

    async def execute_with_proxy(
        self,
        func,
        *args,
        retry_on_failure: bool = True,
        max_retries: int = 3,
        **kwargs
    ):
        """
        Execute an async function with an automatically selected proxy.
        Handles retries with different proxies on failure.

        Args:
            func: Async function to execute (should accept proxy as first argument)
            retry_on_failure: Whether to retry with a different proxy on failure
            max_retries: Maximum number of retry attempts
            *args, **kwargs: Arguments to pass to func

        Returns:
            Result of func
        """
        last_exception = None

        for attempt in range(max_retries):
            proxy = await self.get_proxy()
            if not proxy:
                raise RuntimeError("No proxies available")

            start_time = time.time()
            try:
                result = await func(proxy, *args, **kwargs)
                response_time = (time.time() - start_time) * 1000
                await self.record_request(proxy.url, success=True, response_time_ms=response_time)
                return result

            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                await self.record_request(proxy.url, success=False, response_time_ms=response_time)
                last_exception = e
                logger.warning(f"Request failed with proxy {proxy.url}: {e}")

                if not retry_on_failure or attempt >= max_retries - 1:
                    raise

            finally:
                self.release_proxy(proxy.url)

        if last_exception:
            raise last_exception


# Singleton instance for global use
_global_proxy_pool: Optional[ProxyPool] = None


def get_global_proxy_pool() -> Optional[ProxyPool]:
    """Get the global proxy pool instance."""
    return _global_proxy_pool


def set_global_proxy_pool(pool: ProxyPool):
    """Set the global proxy pool instance."""
    global _global_proxy_pool
    _global_proxy_pool = pool


async def init_proxy_pool_from_env():
    """
    Initialize proxy pool from environment variables.
    Expected format: PROXY_URLS="http://proxy1:8080,http://proxy2:8080"
    """
    import os

    proxy_urls = os.getenv("PROXY_URLS", "").split(",")
    proxy_urls = [url.strip() for url in proxy_urls if url.strip()]

    if not proxy_urls:
        logger.info("No proxies configured in environment")
        return None

    proxies = [ProxyConfig(url=url) for url in proxy_urls]
    pool = ProxyPool(proxies=proxies)
    await pool.start()

    set_global_proxy_pool(pool)
    logger.info(f"Initialized proxy pool with {len(proxies)} proxies")
    return pool
