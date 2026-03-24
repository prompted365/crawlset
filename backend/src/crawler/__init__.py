"""
Web crawler module with advanced features.
"""
# browser imports are intentionally NOT re-exported here.
# Import directly from src.crawler.browser where playwright is available.
from .proxy_pool import (
    ProxyConfig,
    ProxyPool,
    ProxyProtocol,
    ProxyStats,
    get_global_proxy_pool,
    init_proxy_pool_from_env,
    set_global_proxy_pool,
)
from .rate_limiter import (
    DomainStats,
    RateLimitConfig,
    RateLimiter,
    get_global_rate_limiter,
    set_global_rate_limiter,
)

__all__ = [
    # Proxy Pool
    "ProxyConfig",
    "ProxyPool",
    "ProxyProtocol",
    "ProxyStats",
    "get_global_proxy_pool",
    "init_proxy_pool_from_env",
    "set_global_proxy_pool",
    # Rate Limiter
    "DomainStats",
    "RateLimitConfig",
    "RateLimiter",
    "get_global_rate_limiter",
    "set_global_rate_limiter",
]
