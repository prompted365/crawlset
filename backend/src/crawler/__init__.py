"""
Web crawler module with advanced features.
"""
from .browser import (
    BrowserConfig,
    BrowserPool,
    FetchResult,
    PlaywrightBrowser,
    WaitStrategy,
    fetch_page,
)
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
    # Browser
    "BrowserConfig",
    "BrowserPool",
    "FetchResult",
    "PlaywrightBrowser",
    "WaitStrategy",
    "fetch_page",
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
