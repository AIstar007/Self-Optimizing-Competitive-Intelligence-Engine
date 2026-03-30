"""
Browser automation provider using Playwright for web scraping and interaction.

This module implements the BrowserProvider interface using Playwright to automate
web browser operations including:
    - Web searches (Google, Bing)
    - Page navigation and content extraction
    - Element interaction (click, type, submit)
    - Screenshot capture
    - Cookie and session management
    - JavaScript execution
    - Wait conditions (selector, function, navigation)

Features:
    - Full async/await support
    - Multiple browser types (Chromium, Firefox, WebKit)
    - Dynamic page load handling
    - Automatic cookie management
    - Error handling and retry logic
    - Headless and headed mode support
"""

from datetime import datetime
from typing import Any, Optional

from core.domain import (
    BrowserProvider,
    BrowserType,
    PageLoadState,
    SearchResult,
    ScrapedContent,
    NavigationResult,
    Screenshot,
)


class PlaywrightBrowserProvider(BrowserProvider):
    """
    Playwright-based implementation of BrowserProvider.
    
    Provides browser automation capabilities for web scraping, testing, and interaction.
    """

    def __init__(
        self,
        browser_type: BrowserType = BrowserType.CHROMIUM,
        headless: bool = True,
        timeout: int = 30000,  # 30 seconds
    ):
        """
        Initialize Playwright browser provider.
        
        Args:
            browser_type: Type of browser to use (Chromium, Firefox, WebKit)
            headless: Whether to run browser in headless mode
            timeout: Default timeout for operations (milliseconds)
        """
        self.browser_type = browser_type
        self.headless = headless
        self.timeout = timeout
        self.browser = None
        self.context = None
        self.page = None

    async def initialize(self):
        """Initialize browser and context."""
        from playwright.async_api import async_playwright

        self.playwright = await async_playwright().start()

        # Select browser type
        if self.browser_type == BrowserType.CHROMIUM:
            self.browser = await self.playwright.chromium.launch(headless=self.headless)
        elif self.browser_type == BrowserType.FIREFOX:
            self.browser = await self.playwright.firefox.launch(headless=self.headless)
        elif self.browser_type == BrowserType.WEBKIT:
            self.browser = await self.playwright.webkit.launch(headless=self.headless)

        # Create context
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )

        # Create page
        self.page = await self.context.new_page()
        self.page.set_default_timeout(self.timeout)

    async def close(self):
        """Close browser and clean up resources."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def search(
        self,
        query: str,
        search_engine: str = "google",
        num_results: int = 10,
    ) -> list[SearchResult]:
        """
        Perform a web search.
        
        Args:
            query: Search query
            search_engine: Search engine to use (google, bing)
            num_results: Number of results to return
            
        Returns:
            List of search results
        """
        if not self.page:
            await self.initialize()

        results = []

        try:
            if search_engine == "google":
                await self.page.goto("https://www.google.com")
                await self.page.fill("input[name='q']", query)
                await self.page.click("input[value='Google Search']")
                await self.page.wait_for_load_state("networkidle")

                # Extract search results
                search_results = await self.page.query_selector_all("div.g")
                for idx, result in enumerate(search_results[:num_results]):
                    try:
                        title_elem = await result.query_selector("h3")
                        title = await title_elem.inner_text() if title_elem else ""

                        url_elem = await result.query_selector("a")
                        url = await url_elem.get_attribute("href") if url_elem else ""

                        snippet_elem = await result.query_selector("span[data-snippet]")
                        snippet = await snippet_elem.inner_text() if snippet_elem else ""

                        if title and url:
                            results.append(
                                SearchResult(
                                    title=title,
                                    url=url,
                                    snippet=snippet,
                                    position=idx + 1,
                                    source="google",
                                )
                            )
                    except Exception:
                        continue

            elif search_engine == "bing":
                await self.page.goto(f"https://www.bing.com/search?q={query}")
                await self.page.wait_for_load_state("networkidle")

                # Extract Bing results
                search_results = await self.page.query_selector_all("li.b_algo")
                for idx, result in enumerate(search_results[:num_results]):
                    try:
                        title_elem = await result.query_selector("h2 a")
                        title = await title_elem.inner_text() if title_elem else ""

                        url = await title_elem.get_attribute("href") if title_elem else ""

                        snippet_elem = await result.query_selector("p")
                        snippet = await snippet_elem.inner_text() if snippet_elem else ""

                        if title and url:
                            results.append(
                                SearchResult(
                                    title=title,
                                    url=url,
                                    snippet=snippet,
                                    position=idx + 1,
                                    source="bing",
                                )
                            )
                    except Exception:
                        continue

        except Exception as e:
            raise RuntimeError(f"Search failed: {str(e)}")

        return results

    async def navigate(self, url: str, wait_until: str = "load") -> NavigationResult:
        """
        Navigate to a URL.
        
        Args:
            url: URL to navigate to
            wait_until: Wait condition (load, domcontentloaded, networkidle)
            
        Returns:
            NavigationResult with status and details
        """
        if not self.page:
            await self.initialize()

        try:
            response = await self.page.goto(url, wait_until=wait_until)
            return NavigationResult(
                success=response and response.ok,
                url=self.page.url,
                status=response.status if response else 0,
                error=None,
            )
        except Exception as e:
            return NavigationResult(
                success=False,
                url=url,
                status=0,
                error=str(e),
            )

    async def get_page_content(self) -> str:
        """
        Get full page HTML content.
        
        Returns:
            Page HTML content
        """
        if not self.page:
            await self.initialize()

        return await self.page.content()

    async def get_page_title(self) -> str:
        """
        Get page title.
        
        Returns:
            Page title
        """
        if not self.page:
            await self.initialize()

        return await self.page.title()

    async def get_scraped_content(
        self,
        url: str,
        wait_selector: Optional[str] = None,
    ) -> ScrapedContent:
        """
        Navigate to URL and scrape content.
        
        Args:
            url: URL to scrape
            wait_selector: CSS selector to wait for before scraping
            
        Returns:
            ScrapedContent with extracted data
        """
        if not self.page:
            await self.initialize()

        try:
            await self.navigate(url)

            if wait_selector:
                await self.page.wait_for_selector(wait_selector)

            # Extract content
            content = await self.page.content()
            title = await self.page.title()

            # Extract text
            text_content = await self.page.evaluate("() => document.body.innerText")

            # Extract links
            links = await self.page.evaluate(
                """() => Array.from(document.querySelectorAll('a'))
                   .map(a => ({text: a.innerText, href: a.href}))"""
            )

            # Extract images
            images = await self.page.evaluate(
                """() => Array.from(document.querySelectorAll('img'))
                   .map(img => ({src: img.src, alt: img.alt}))"""
            )

            return ScrapedContent(
                url=self.page.url,
                title=title,
                content=text_content,
                metadata={
                    "html": content,
                    "timestamp": datetime.utcnow().isoformat(),
                },
                links=[link["href"] for link in links if link.get("href")],
                images=[img["src"] for img in images if img.get("src")],
            )
        except Exception as e:
            raise RuntimeError(f"Content scraping failed: {str(e)}")

    async def find_elements(self, selector: str) -> list[dict]:
        """
        Find elements by CSS selector.
        
        Args:
            selector: CSS selector
            
        Returns:
            List of element information
        """
        if not self.page:
            await self.initialize()

        elements = await self.page.query_selector_all(selector)
        results = []

        for elem in elements:
            try:
                results.append({
                    "tag": await elem.evaluate("el => el.tagName"),
                    "text": await elem.inner_text(),
                    "html": await elem.inner_html(),
                })
            except Exception:
                continue

        return results

    async def click(self, selector: str) -> bool:
        """
        Click an element.
        
        Args:
            selector: CSS selector of element to click
            
        Returns:
            True if successful
        """
        if not self.page:
            await self.initialize()

        try:
            await self.page.click(selector)
            return True
        except Exception:
            return False

    async def type_text(self, selector: str, text: str) -> bool:
        """
        Type text in an input element.
        
        Args:
            selector: CSS selector of input element
            text: Text to type
            
        Returns:
            True if successful
        """
        if not self.page:
            await self.initialize()

        try:
            await self.page.fill(selector, text)
            return True
        except Exception:
            return False

    async def wait_for_selector(self, selector: str, timeout: int = 30000) -> bool:
        """
        Wait for element to appear.
        
        Args:
            selector: CSS selector
            timeout: Timeout in milliseconds
            
        Returns:
            True if element appeared
        """
        if not self.page:
            await self.initialize()

        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception:
            return False

    async def wait_for_function(self, function: str, timeout: int = 30000) -> bool:
        """
        Wait for JavaScript function to return true.
        
        Args:
            function: JavaScript function
            timeout: Timeout in milliseconds
            
        Returns:
            True if function returned true
        """
        if not self.page:
            await self.initialize()

        try:
            await self.page.wait_for_function(function, timeout=timeout)
            return True
        except Exception:
            return False

    async def screenshot(self, full_page: bool = False) -> Screenshot:
        """
        Take a screenshot of the page.
        
        Args:
            full_page: Whether to capture full page height
            
        Returns:
            Screenshot with image data
        """
        if not self.page:
            await self.initialize()

        try:
            image_data = await self.page.screenshot(full_page=full_page)

            viewport = await self.page.evaluate("() => ({width: window.innerWidth, height: window.innerHeight})")

            return Screenshot(
                data=image_data,
                format="png",
                width=viewport.get("width", 1920),
                height=viewport.get("height", 1080),
            )
        except Exception as e:
            raise RuntimeError(f"Screenshot failed: {str(e)}")

    async def get_cookies(self) -> list[dict]:
        """
        Get all cookies for the current page.
        
        Returns:
            List of cookie dictionaries
        """
        if not self.context:
            await self.initialize()

        return await self.context.cookies()

    async def set_cookies(self, cookies: list[dict]) -> None:
        """
        Set cookies for the context.
        
        Args:
            cookies: List of cookie dictionaries
        """
        if not self.context:
            await self.initialize()

        await self.context.add_cookies(cookies)

    async def accept_cookies(self, selector: Optional[str] = None) -> bool:
        """
        Accept cookies by clicking accept button.
        
        Args:
            selector: CSS selector of accept button
            
        Returns:
            True if successful
        """
        if not self.page:
            await self.initialize()

        # Common cookie accept selectors
        selectors = [
            selector,
            "button:has-text('Accept')",
            "button:has-text('Accept All')",
            "button[class*='accept']",
            "[class*='cookie'] button",
        ]

        for sel in selectors:
            if sel and await self.click(sel):
                return True

        return False

    async def execute_script(self, script: str, *args) -> Any:
        """
        Execute JavaScript on the page.
        
        Args:
            script: JavaScript code
            *args: Arguments to pass to the script
            
        Returns:
            Result of script execution
        """
        if not self.page:
            await self.initialize()

        return await self.page.evaluate(script, args)


__all__ = [
    "PlaywrightBrowserProvider",
]
