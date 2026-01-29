"""
Advanced Playwright browser wrapper with smart wait strategies, anti-bot detection,
cookie/session management, screenshot capture, and JavaScript execution.
"""
from __future__ import annotations

import asyncio
import base64
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal
from urllib.parse import urlparse

import httpx
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright, Error as PlaywrightError

logger = logging.getLogger(__name__)


@dataclass
class BrowserConfig:
    """Configuration for browser instance."""
    headless: bool = True
    user_agent: Optional[str] = None
    viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1920, "height": 1080})
    locale: str = "en-US"
    timezone: str = "America/New_York"
    device_scale_factor: float = 1.0
    has_touch: bool = False
    is_mobile: bool = False
    proxy: Optional[Dict[str, str]] = None
    bypass_csp: bool = True
    java_script_enabled: bool = True
    ignore_https_errors: bool = True
    extra_http_headers: Optional[Dict[str, str]] = None
    geolocation: Optional[Dict[str, float]] = None
    permissions: List[str] = field(default_factory=list)
    color_scheme: Literal["light", "dark", "no-preference"] = "light"
    timeout: float = 30000  # milliseconds


@dataclass
class WaitStrategy:
    """Wait strategy configuration."""
    wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] = "networkidle"
    additional_wait_ms: int = 0  # Additional wait after initial load
    wait_for_selector: Optional[str] = None  # CSS selector to wait for
    wait_for_function: Optional[str] = None  # JS function to wait for
    timeout: Optional[float] = None  # Override default timeout


@dataclass
class FetchResult:
    """Result of a page fetch operation."""
    url: str
    html: str
    status: int
    headers: Dict[str, str]
    cookies: List[Dict[str, Any]]
    screenshot: Optional[str] = None  # base64 encoded
    console_logs: List[str] = field(default_factory=list)
    network_logs: List[Dict[str, Any]] = field(default_factory=list)
    redirected_url: Optional[str] = None
    load_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BrowserPool:
    """Manages a pool of browser instances for reuse."""

    def __init__(self, max_browsers: int = 5, max_contexts_per_browser: int = 10):
        self.max_browsers = max_browsers
        self.max_contexts_per_browser = max_contexts_per_browser
        self._playwright: Optional[Playwright] = None
        self._browsers: List[Browser] = []
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize the browser pool."""
        if self._playwright is None:
            self._playwright = await async_playwright().start()

    async def close(self):
        """Close all browsers in the pool."""
        for browser in self._browsers:
            await browser.close()
        self._browsers.clear()
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    @asynccontextmanager
    async def get_browser(self, config: BrowserConfig):
        """Get a browser instance from the pool."""
        async with self._lock:
            if not self._playwright:
                await self.initialize()

            # Launch new browser if pool not full
            if len(self._browsers) < self.max_browsers:
                browser = await self._launch_browser(config)
                self._browsers.append(browser)
            else:
                # Reuse existing browser
                browser = self._browsers[0]

        try:
            yield browser
        finally:
            # Keep browser in pool for reuse
            pass

    async def _launch_browser(self, config: BrowserConfig) -> Browser:
        """Launch a new browser instance."""
        launch_options = {
            "headless": config.headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        }

        if config.proxy:
            launch_options["proxy"] = config.proxy

        browser = await self._playwright.chromium.launch(**launch_options)
        return browser


class PlaywrightBrowser:
    """
    Advanced Playwright browser wrapper with comprehensive features:
    - Smart wait strategies (network idle, DOM mutations, custom selectors)
    - Cookie/session management with persistence
    - Screenshot capture in multiple formats
    - JavaScript execution with result extraction
    - Anti-bot detection bypass techniques
    - Request/response interception
    - Console and network logging
    """

    def __init__(self, config: Optional[BrowserConfig] = None, pool: Optional[BrowserPool] = None):
        self.config = config or BrowserConfig()
        self.pool = pool
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._playwright: Optional[Playwright] = None
        self._standalone = pool is None
        self._console_logs: List[str] = []
        self._network_logs: List[Dict[str, Any]] = []

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def initialize(self):
        """Initialize the browser, context, and page."""
        if self.pool:
            # Use browser pool
            self._browser = await self.pool.get_browser(self.config).__aenter__()
        else:
            # Standalone browser
            self._playwright = await async_playwright().start()
            self._browser = await self._launch_browser()

        self._context = await self._create_context()
        self._page = await self._context.new_page()

        # Set up logging
        self._page.on("console", lambda msg: self._console_logs.append(f"[{msg.type}] {msg.text}"))
        self._page.on("request", lambda req: self._network_logs.append({
            "type": "request", "method": req.method, "url": req.url, "headers": req.headers
        }))
        self._page.on("response", lambda res: self._network_logs.append({
            "type": "response", "status": res.status, "url": res.url, "headers": res.headers
        }))

    async def close(self):
        """Close browser resources."""
        if self._page:
            await self._page.close()
        if self._context:
            await self._context.close()
        if self._standalone and self._browser:
            await self._browser.close()
        if self._standalone and self._playwright:
            await self._playwright.stop()

    async def _launch_browser(self) -> Browser:
        """Launch a new browser instance with anti-detection measures."""
        launch_options = {
            "headless": self.config.headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--window-size=1920,1080",
            ],
        }

        if self.config.proxy:
            launch_options["proxy"] = self.config.proxy

        return await self._playwright.chromium.launch(**launch_options)

    async def _create_context(self) -> BrowserContext:
        """Create a browser context with anti-detection measures."""
        context_options = {
            "viewport": self.config.viewport,
            "locale": self.config.locale,
            "timezone_id": self.config.timezone,
            "device_scale_factor": self.config.device_scale_factor,
            "has_touch": self.config.has_touch,
            "is_mobile": self.config.is_mobile,
            "bypass_csp": self.config.bypass_csp,
            "java_script_enabled": self.config.java_script_enabled,
            "ignore_https_errors": self.config.ignore_https_errors,
            "color_scheme": self.config.color_scheme,
        }

        if self.config.user_agent:
            context_options["user_agent"] = self.config.user_agent

        if self.config.extra_http_headers:
            context_options["extra_http_headers"] = self.config.extra_http_headers

        if self.config.geolocation:
            context_options["geolocation"] = self.config.geolocation

        if self.config.permissions:
            context_options["permissions"] = self.config.permissions

        context = await self._browser.new_context(**context_options)

        # Anti-detection: Remove webdriver property
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Mock plugins and languages
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });

            // Mock chrome object
            window.chrome = {
                runtime: {}
            };

            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

        return context

    async def fetch(
        self,
        url: str,
        wait_strategy: Optional[WaitStrategy] = None,
        take_screenshot: bool = False,
        screenshot_format: Literal["png", "jpeg"] = "png",
        execute_js: Optional[str] = None,
        cookies: Optional[List[Dict[str, Any]]] = None,
    ) -> FetchResult:
        """
        Fetch a page with advanced wait strategies and optional features.

        Args:
            url: URL to fetch
            wait_strategy: Custom wait strategy
            take_screenshot: Whether to take a screenshot
            screenshot_format: Screenshot format (png or jpeg)
            execute_js: JavaScript to execute before returning
            cookies: Cookies to set before navigation

        Returns:
            FetchResult with page content and metadata
        """
        if not self._page:
            raise RuntimeError("Browser not initialized. Call initialize() or use as context manager.")

        # Clear logs
        self._console_logs.clear()
        self._network_logs.clear()

        # Set cookies if provided
        if cookies:
            await self._context.add_cookies(cookies)

        # Apply wait strategy
        strategy = wait_strategy or WaitStrategy()
        timeout = strategy.timeout or self.config.timeout

        # Navigate to page
        start_time = asyncio.get_event_loop().time()
        try:
            response = await self._page.goto(
                url,
                wait_until=strategy.wait_until,
                timeout=timeout
            )

            # Additional waits
            if strategy.additional_wait_ms > 0:
                await asyncio.sleep(strategy.additional_wait_ms / 1000.0)

            if strategy.wait_for_selector:
                await self._page.wait_for_selector(strategy.wait_for_selector, timeout=timeout)

            if strategy.wait_for_function:
                await self._page.wait_for_function(strategy.wait_for_function, timeout=timeout)

            # Execute custom JavaScript if provided
            js_result = None
            if execute_js:
                js_result = await self._page.evaluate(execute_js)

            # Get page content
            html = await self._page.content()

            # Take screenshot if requested
            screenshot_b64 = None
            if take_screenshot:
                screenshot_bytes = await self._page.screenshot(
                    type=screenshot_format,
                    full_page=True
                )
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

            # Get cookies
            cookies_list = await self._context.cookies()

            # Calculate load time
            load_time = (asyncio.get_event_loop().time() - start_time) * 1000

            # Build result
            result = FetchResult(
                url=url,
                html=html,
                status=response.status if response else 0,
                headers=dict(response.headers) if response else {},
                cookies=cookies_list,
                screenshot=screenshot_b64,
                console_logs=self._console_logs.copy(),
                network_logs=self._network_logs.copy(),
                redirected_url=response.url if response and response.url != url else None,
                load_time_ms=load_time,
                metadata={"js_result": js_result} if js_result else {}
            )

            return result

        except PlaywrightError as e:
            logger.error(f"Playwright error fetching {url}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            raise

    async def execute_script(self, script: str) -> Any:
        """Execute JavaScript and return the result."""
        if not self._page:
            raise RuntimeError("Browser not initialized")
        return await self._page.evaluate(script)

    async def wait_for_element(self, selector: str, timeout: Optional[float] = None) -> bool:
        """Wait for an element to appear."""
        if not self._page:
            raise RuntimeError("Browser not initialized")
        try:
            await self._page.wait_for_selector(selector, timeout=timeout or self.config.timeout)
            return True
        except PlaywrightError:
            return False

    async def click(self, selector: str):
        """Click an element."""
        if not self._page:
            raise RuntimeError("Browser not initialized")
        await self._page.click(selector)

    async def fill(self, selector: str, value: str):
        """Fill an input field."""
        if not self._page:
            raise RuntimeError("Browser not initialized")
        await self._page.fill(selector, value)

    async def get_cookies(self) -> List[Dict[str, Any]]:
        """Get all cookies from the current context."""
        if not self._context:
            raise RuntimeError("Browser not initialized")
        return await self._context.cookies()

    async def set_cookies(self, cookies: List[Dict[str, Any]]):
        """Set cookies in the current context."""
        if not self._context:
            raise RuntimeError("Browser not initialized")
        await self._context.add_cookies(cookies)

    async def clear_cookies(self):
        """Clear all cookies from the current context."""
        if not self._context:
            raise RuntimeError("Browser not initialized")
        await self._context.clear_cookies()

    async def save_session(self, path: Path):
        """Save browser session (cookies and storage) to disk."""
        if not self._context:
            raise RuntimeError("Browser not initialized")
        await self._context.storage_state(path=str(path))

    async def load_session(self, path: Path):
        """Load browser session from disk."""
        # Must be called before creating context
        raise NotImplementedError("Load session during context creation instead")


async def fetch_page(
    url: str,
    use_playwright: Optional[bool] = None,
    config: Optional[BrowserConfig] = None,
    wait_strategy: Optional[WaitStrategy] = None,
    take_screenshot: bool = False,
) -> str:
    """
    Convenience function to fetch a page. Falls back to httpx if Playwright is disabled.

    Args:
        url: URL to fetch
        use_playwright: Force Playwright usage (default: auto-detect)
        config: Browser configuration
        wait_strategy: Wait strategy
        take_screenshot: Whether to take screenshot

    Returns:
        HTML content as string
    """
    import os

    use_pw = use_playwright if use_playwright is not None else os.getenv("USE_PLAYWRIGHT", "0") == "1"

    if use_pw:
        try:
            async with PlaywrightBrowser(config=config) as browser:
                result = await browser.fetch(
                    url,
                    wait_strategy=wait_strategy,
                    take_screenshot=take_screenshot
                )
                return result.html
        except Exception as e:
            logger.warning(f"Playwright fetch failed, falling back to httpx: {e}")

    # Fallback to httpx
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.text
