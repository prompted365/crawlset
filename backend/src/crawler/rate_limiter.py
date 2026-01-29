"""
Per-domain rate limiter with exponential backoff, domain-based queuing,
and concurrent request limits.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Callable, Deque, Dict, Optional, Set
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration for a domain."""
    requests_per_second: float = 1.0
    max_concurrent: int = 5
    burst_size: int = 10  # Max requests in burst
    backoff_base: float = 2.0  # Exponential backoff base
    backoff_max: float = 300.0  # Max backoff time in seconds
    backoff_factor: float = 1.0  # Multiplier for backoff time
    respect_retry_after: bool = True  # Respect Retry-After header
    cooldown_on_error: float = 60.0  # Cooldown period after error (seconds)


@dataclass
class DomainStats:
    """Statistics for a domain."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limited_count: int = 0
    current_concurrent: int = 0
    last_request_time: float = 0.0
    last_error_time: float = 0.0
    consecutive_errors: int = 0
    current_backoff: float = 0.0
    retry_after_until: float = 0.0
    request_times: Deque[float] = field(default_factory=lambda: deque(maxlen=100))

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests

    @property
    def average_request_interval(self) -> float:
        """Calculate average time between requests."""
        if len(self.request_times) < 2:
            return 0.0
        times = list(self.request_times)
        intervals = [times[i] - times[i - 1] for i in range(1, len(times))]
        return sum(intervals) / len(intervals) if intervals else 0.0


class RateLimiter:
    """
    Per-domain rate limiter with:
    - Configurable requests per second per domain
    - Concurrent request limiting per domain
    - Token bucket algorithm for burst handling
    - Exponential backoff on errors
    - Respect for Retry-After headers
    - Domain-based request queuing
    """

    def __init__(
        self,
        default_config: Optional[RateLimitConfig] = None,
        auto_adjust: bool = True,
    ):
        """
        Initialize rate limiter.

        Args:
            default_config: Default rate limit configuration
            auto_adjust: Automatically adjust rate limits based on responses
        """
        self.default_config = default_config or RateLimitConfig()
        self.auto_adjust = auto_adjust

        # Per-domain configurations
        self._domain_configs: Dict[str, RateLimitConfig] = {}
        self._domain_stats: Dict[str, DomainStats] = defaultdict(DomainStats)

        # Concurrency control
        self._semaphores: Dict[str, asyncio.Semaphore] = {}
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

        # Token buckets (domain -> tokens available)
        self._token_buckets: Dict[str, float] = {}
        self._last_refill: Dict[str, float] = {}

        # Request queues (domain -> queue of waiting coroutines)
        self._queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc or parsed.path

    def get_config(self, domain: str) -> RateLimitConfig:
        """Get rate limit configuration for a domain."""
        return self._domain_configs.get(domain, self.default_config)

    def set_config(self, domain: str, config: RateLimitConfig):
        """Set rate limit configuration for a domain."""
        self._domain_configs[domain] = config
        # Reset semaphore for new concurrent limit
        self._semaphores[domain] = asyncio.Semaphore(config.max_concurrent)
        logger.info(f"Set rate limit config for {domain}: {config.requests_per_second} req/s")

    def get_stats(self, domain: str) -> DomainStats:
        """Get statistics for a domain."""
        return self._domain_stats[domain]

    def get_all_stats(self) -> Dict[str, DomainStats]:
        """Get statistics for all domains."""
        return dict(self._domain_stats)

    def _get_or_create_semaphore(self, domain: str) -> asyncio.Semaphore:
        """Get or create semaphore for domain."""
        if domain not in self._semaphores:
            config = self.get_config(domain)
            self._semaphores[domain] = asyncio.Semaphore(config.max_concurrent)
        return self._semaphores[domain]

    def _refill_tokens(self, domain: str):
        """Refill token bucket for domain."""
        config = self.get_config(domain)
        now = time.time()

        # Initialize if first time
        if domain not in self._token_buckets:
            self._token_buckets[domain] = config.burst_size
            self._last_refill[domain] = now
            return

        # Calculate tokens to add based on time elapsed
        elapsed = now - self._last_refill[domain]
        tokens_to_add = elapsed * config.requests_per_second

        # Add tokens up to burst size
        self._token_buckets[domain] = min(
            config.burst_size,
            self._token_buckets[domain] + tokens_to_add
        )
        self._last_refill[domain] = now

    def _consume_token(self, domain: str) -> bool:
        """
        Try to consume a token from the bucket.

        Returns:
            True if token was consumed, False if bucket is empty
        """
        self._refill_tokens(domain)

        if self._token_buckets[domain] >= 1.0:
            self._token_buckets[domain] -= 1.0
            return True
        return False

    def _calculate_backoff(self, domain: str) -> float:
        """Calculate backoff time for domain based on consecutive errors."""
        stats = self._domain_stats[domain]
        config = self.get_config(domain)

        if stats.consecutive_errors == 0:
            return 0.0

        # Exponential backoff: base^errors * factor
        backoff = (config.backoff_base ** stats.consecutive_errors) * config.backoff_factor
        return min(backoff, config.backoff_max)

    async def _wait_for_rate_limit(self, domain: str):
        """Wait until rate limit allows request."""
        config = self.get_config(domain)
        stats = self._domain_stats[domain]

        # Check for Retry-After
        if config.respect_retry_after and stats.retry_after_until > time.time():
            wait_time = stats.retry_after_until - time.time()
            logger.info(f"Waiting {wait_time:.2f}s for Retry-After on {domain}")
            await asyncio.sleep(wait_time)
            stats.retry_after_until = 0.0

        # Check for backoff
        if stats.current_backoff > 0 and stats.last_error_time > 0:
            time_since_error = time.time() - stats.last_error_time
            if time_since_error < stats.current_backoff:
                wait_time = stats.current_backoff - time_since_error
                logger.info(f"Backing off {wait_time:.2f}s for {domain}")
                await asyncio.sleep(wait_time)
                stats.current_backoff = 0.0

        # Wait for token availability
        while not self._consume_token(domain):
            # Calculate time until next token
            tokens_needed = 1.0 - self._token_buckets[domain]
            wait_time = tokens_needed / config.requests_per_second
            await asyncio.sleep(wait_time)
            self._refill_tokens(domain)

    async def acquire(self, url: str) -> str:
        """
        Acquire permission to make a request to the URL.
        This handles rate limiting and concurrency control.

        Args:
            url: URL to request

        Returns:
            Domain string (for use with release)
        """
        domain = self._extract_domain(url)
        config = self.get_config(domain)
        stats = self._domain_stats[domain]
        semaphore = self._get_or_create_semaphore(domain)

        # Wait for rate limit
        await self._wait_for_rate_limit(domain)

        # Acquire concurrency slot
        await semaphore.acquire()

        # Update stats
        stats.current_concurrent += 1
        stats.total_requests += 1
        stats.last_request_time = time.time()
        stats.request_times.append(time.time())

        return domain

    def release(self, domain: str):
        """
        Release a request slot for the domain.

        Args:
            domain: Domain to release (returned from acquire)
        """
        if domain in self._semaphores:
            stats = self._domain_stats[domain]
            stats.current_concurrent -= 1
            self._semaphores[domain].release()

    def record_success(self, domain: str):
        """Record a successful request for the domain."""
        stats = self._domain_stats[domain]
        stats.successful_requests += 1
        stats.consecutive_errors = 0
        stats.current_backoff = 0.0

        # Auto-adjust: Gradually increase rate if successful
        if self.auto_adjust and stats.success_rate > 0.95:
            self._maybe_increase_rate(domain)

    def record_failure(
        self,
        domain: str,
        is_rate_limit: bool = False,
        retry_after: Optional[float] = None
    ):
        """
        Record a failed request for the domain.

        Args:
            domain: Domain that failed
            is_rate_limit: Whether failure was due to rate limiting (429)
            retry_after: Retry-After value in seconds
        """
        stats = self._domain_stats[domain]
        stats.failed_requests += 1
        stats.consecutive_errors += 1
        stats.last_error_time = time.time()

        if is_rate_limit:
            stats.rate_limited_count += 1

        # Set retry_after if provided
        if retry_after:
            stats.retry_after_until = time.time() + retry_after

        # Calculate and set backoff
        stats.current_backoff = self._calculate_backoff(domain)

        # Auto-adjust: Decrease rate on repeated failures
        if self.auto_adjust and stats.consecutive_errors >= 3:
            self._decrease_rate(domain)

    def _maybe_increase_rate(self, domain: str):
        """Gradually increase rate limit if performing well."""
        if domain not in self._domain_configs:
            return

        config = self._domain_configs[domain]
        stats = self._domain_stats[domain]

        # Only increase if we have enough data
        if stats.total_requests < 100:
            return

        # Increase by 10%
        new_rate = config.requests_per_second * 1.1
        max_rate = self.default_config.requests_per_second * 2.0

        if new_rate <= max_rate:
            config.requests_per_second = new_rate
            logger.info(f"Increased rate limit for {domain} to {new_rate:.2f} req/s")

    def _decrease_rate(self, domain: str):
        """Decrease rate limit due to errors."""
        config = self.get_config(domain)
        stats = self._domain_stats[domain]

        # Decrease by 50%
        new_rate = config.requests_per_second * 0.5
        min_rate = 0.1  # Minimum 1 request per 10 seconds

        if new_rate >= min_rate:
            if domain not in self._domain_configs:
                # Create new config based on default
                self._domain_configs[domain] = RateLimitConfig(
                    requests_per_second=new_rate,
                    max_concurrent=config.max_concurrent,
                    burst_size=config.burst_size,
                )
            else:
                self._domain_configs[domain].requests_per_second = new_rate

            logger.warning(
                f"Decreased rate limit for {domain} to {new_rate:.2f} req/s "
                f"due to {stats.consecutive_errors} consecutive errors"
            )

    async def execute(
        self,
        url: str,
        func: Callable,
        *args,
        record_result: bool = True,
        **kwargs
    ):
        """
        Execute a function with rate limiting.

        Args:
            url: URL being requested
            func: Async function to execute
            record_result: Whether to record success/failure
            *args, **kwargs: Arguments to pass to func

        Returns:
            Result of func
        """
        domain = await self.acquire(url)

        try:
            result = await func(*args, **kwargs)
            if record_result:
                self.record_success(domain)
            return result

        except Exception as e:
            if record_result:
                # Check if it's a rate limit error
                is_rate_limit = False
                retry_after = None

                # Try to extract rate limit info from common exception types
                if hasattr(e, 'response'):
                    response = e.response
                    if hasattr(response, 'status_code') and response.status_code == 429:
                        is_rate_limit = True
                        if hasattr(response, 'headers'):
                            retry_after_header = response.headers.get('Retry-After')
                            if retry_after_header:
                                try:
                                    retry_after = float(retry_after_header)
                                except ValueError:
                                    pass

                self.record_failure(domain, is_rate_limit=is_rate_limit, retry_after=retry_after)

            raise

        finally:
            self.release(domain)

    def reset_domain(self, domain: str):
        """Reset statistics and state for a domain."""
        if domain in self._domain_stats:
            self._domain_stats[domain] = DomainStats()
        if domain in self._token_buckets:
            del self._token_buckets[domain]
        if domain in self._last_refill:
            del self._last_refill[domain]
        logger.info(f"Reset rate limiter state for {domain}")

    def clear_all(self):
        """Clear all statistics and state."""
        self._domain_stats.clear()
        self._token_buckets.clear()
        self._last_refill.clear()
        logger.info("Cleared all rate limiter state")


# Global rate limiter instance
_global_rate_limiter: Optional[RateLimiter] = None


def get_global_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter instance."""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter()
    return _global_rate_limiter


def set_global_rate_limiter(limiter: RateLimiter):
    """Set the global rate limiter instance."""
    global _global_rate_limiter
    _global_rate_limiter = limiter
