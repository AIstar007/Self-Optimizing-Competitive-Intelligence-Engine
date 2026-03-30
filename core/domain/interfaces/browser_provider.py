"""
Domain Browser Provider Interface

Defines the contract for browser automation and web interaction.
The infrastructure layer implements this interface.

Following Dependency Inversion Principle - the domain layer
defines what it needs from browser automation without coupling
to specific implementations (Playwright, Selenium, etc.).
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, AsyncIterator
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class BrowserType(Enum):
    """Supported browser types."""
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class PageLoadState(Enum):
    """Page load states."""
    DOMCONTENTLOADED = "domcontentloaded"
    LOAD = "load"
    NETWORKIDLE = "networkidle"


@dataclass(frozen=True)
class SearchResult:
    """
    A search result from a search engine.

    Attributes:
        title: Page title
        url: Page URL
        snippet: Description snippet
        position: Position in results
        source: Source of the result
    """
    title: str
    url: str
    snippet: str
    position: int
    source: str = "google"


@dataclass(frozen=True)
class ScrapedContent:
    """
    Content scraped from a web page.

    Attributes:
        url: The URL of the page
        title: Page title
        content: Main content text
        metadata: Page metadata
        links: List of links found on the page
        images: List of images found on the page
        timestamp: When the content was scraped
    """
    url: str
    title: str
    content: str
    metadata: Dict[str, Any]
    links: List[Dict[str, Any]]
    images: List[Dict[str, Any]]
    timestamp: datetime


@dataclass(frozen=True)
class NavigationResult:
    """
    Result of a navigation operation.

    Attributes:
        success: Whether navigation succeeded
        url: Final URL (after redirects)
        status: HTTP status code
        error: Error message if failed
    """
    success: bool
    url: str
    status: Optional[int]
    error: Optional[str]


@dataclass(frozen=True)
class Screenshot:
    """
    A screenshot of a page.

    Attributes:
        data: Binary screenshot data
        format: Image format (png, jpeg, etc.)
        width: Image width
        height: Image height
        timestamp: When screenshot was taken
    """
    data: bytes
    format: str
    width: int
    height: int
    timestamp: datetime


@dataclass(frozen=True)
class BrowserState:
    """
    Current state of the browser.

    Attributes:
        current_url: Current page URL
        title: Current page title
        is_loading: Whether page is loading
        cookie_count: Number of cookies
        storage_keys: Storage keys
    """
    current_url: str
    title: str
    is_loading: bool
    cookie_count: int
    storage_keys: List[str]


# ============================================================================
# Browser Provider Interface
# ============================================================================


class BrowserProvider(ABC):
    """
    Interface for browser automation and web interaction.

    Provides methods for:
    - Navigating to pages
    - Scraping content
    - Taking screenshots
    - Managing cookies and storage
    """

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the browser is available."""
        pass

    @property
    @abstractmethod
    def current_url(self) -> Optional[str]:
        """Get the current page URL."""
        pass

    @property
    @abstractmethod
    def current_title(self) -> Optional[str]:
        """Get the current page title."""
        pass

    @abstractmethod
    async def start(
        self,
        headless: bool = True,
        browser_type: BrowserType = BrowserType.CHROMIUM,
    ) -> None:
        """
        Start the browser.

        Args:
            headless: Run in headless mode
            browser_type: Type of browser to use
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the browser and clean up."""
        pass

    @abstractmethod
    async def navigate(
        self,
        url: str,
        wait_until: PageLoadState = PageLoadState.LOAD,
        timeout: int = 30000,
    ) -> NavigationResult:
        """
        Navigate to a URL.

        Args:
            url: The URL to navigate to
            wait_until: Wait condition for page load
            timeout: Timeout in milliseconds

        Returns:
            NavigationResult with status
        """
        pass

    @abstractmethod
    async def go_back(self) -> NavigationResult:
        """Go back to the previous page."""
        pass

    @abstractmethod
    async def go_forward(self) -> NavigationResult:
        """Go forward to the next page."""
        pass

    @abstractmethod
    async def refresh(self) -> NavigationResult:
        """Refresh the current page."""
        pass

    @abstractmethod
    async def get_content(self) -> str:
        """Get the full HTML content of the current page."""
        pass

    @abstractmethod
    async def get_text_content(
        self,
        selector: Optional[str] = None,
    ) -> str:
        """
        Get text content from the page.

        Args:
            selector: CSS selector to extract from (None for full page)

        Returns:
            Text content
        """
        pass

    @abstractmethod
    async def get_attribute(
        self,
        selector: str,
        attribute: str,
    ) -> Optional[str]:
        """
        Get an attribute from an element.

        Args:
            selector: CSS selector for the element
            attribute: Attribute name

        Returns:
            Attribute value or None
        """
        pass

    @abstractmethod
    async def scrape_page(
        self,
        url: Optional[str] = None,
        content_selectors: Optional[List[str]] = None,
        metadata_selectors: Optional[Dict[str, str]] = None,
    ) -> ScrapedContent:
        """
        Scrape content from a page.

        Args:
            url: URL to scrape (None for current page)
            content_selectors: CSS selectors for content areas
            metadata_selectors: Mapping of metadata name to CSS selector

        Returns:
            ScrapedContent with extracted data
        """
        pass

    @abstractmethod
    async def take_screenshot(
        self,
        full_page: bool = False,
        selector: Optional[str] = None,
        format: str = "png",
    ) -> Screenshot:
        """
        Take a screenshot.

        Args:
            full_page: Capture the full page
            selector: CSS selector to capture specific element
            format: Image format

        Returns:
            Screenshot object
        """
        pass

    @abstractmethod
    async def click(
        self,
        selector: str,
        timeout: int = 30000,
    ) -> bool:
        """
        Click an element.

        Args:
            selector: CSS selector for the element
            timeout: Timeout in milliseconds

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def type_text(
        self,
        selector: str,
        text: str,
        clear_first: bool = True,
        timeout: int = 30000,
    ) -> bool:
        """
        Type text into an element.

        Args:
            selector: CSS selector for the element
            text: Text to type
            clear_first: Clear existing text first
            timeout: Timeout in milliseconds

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def wait_for_selector(
        self,
        selector: str,
        timeout: int = 30000,
    ) -> bool:
        """
        Wait for a selector to appear.

        Args:
            selector: CSS selector to wait for
            timeout: Timeout in milliseconds

        Returns:
            True if element appeared
        """
        pass

    @abstractmethod
    async def wait_for_navigation(
        self,
        timeout: int = 30000,
    ) -> NavigationResult:
        """
        Wait for a navigation to complete.

        Args:
            timeout: Timeout in milliseconds

        Returns:
            NavigationResult
        """
        pass

    @abstractmethod
    async def execute_script(
        self,
        script: str,
    ) -> Any:
        """
        Execute JavaScript in the page context.

        Args:
            script: JavaScript code to execute

        Returns:
            Script return value
        """
        pass

    @abstractmethod
    async def get_cookies(
        self,
        urls: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get cookies.

        Args:
            urls: Optional list of URLs to filter cookies

        Returns:
            List of cookies
        """
        pass

    @abstractmethod
    async def set_cookies(
        self,
        cookies: List[Dict[str, Any]],
    ) -> None:
        """
        Set cookies.

        Args:
            cookies: List of cookie dictionaries
        """
        pass

    @abstractmethod
    async def clear_cookies(self) -> None:
        """Clear all cookies."""
        pass

    @abstractmethod
    async def get_storage(
        self,
        origin: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Get localStorage contents.

        Args:
            origin: Origin to get storage for

        Returns:
            Storage key-value pairs
        """
        pass

    @abstractmethod
    async def set_storage(
        self,
        data: Dict[str, str],
        origin: Optional[str] = None,
    ) -> None:
        """
        Set localStorage contents.

        Args:
            data: Key-value pairs to set
            origin: Origin to set storage for
        """
        pass

    @abstractmethod
    async def get_state(self) -> BrowserState:
        """Get the current browser state."""
        pass

    @abstractmethod
    async def evaluate(
        self,
        expression: str,
    ) -> Any:
        """
        Evaluate an expression in the page context.

        Args:
            expression: JavaScript expression to evaluate

        Returns:
            Evaluation result
        """
        pass

    @abstractmethod
    async def wait_for(
        self,
        predicate: str,
        timeout: int = 30000,
    ) -> bool:
        """
        Wait for a predicate to become true.

        Args:
            predicate: JavaScript predicate expression
            timeout: Timeout in milliseconds

        Returns:
            True if predicate became true
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the current page/context."""
        pass

    @abstractmethod
    async def new_page(self) -> None:
        """Open a new page."""
        pass

    @abstractmethod
    async def get_page_count(self) -> int:
        """Get the number of open pages."""
        pass


# ============================================================================
# Search Engine Interface
# ============================================================================


class SearchEngine(ABC):
    """
    Interface for search engine interaction.

    Provides methods for performing web searches.
    """

    @abstractmethod
    async def search(
        self,
        query: str,
        num_results: int = 10,
        time_range: Optional[str] = None,
        site: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Perform a web search.

        Args:
            query: Search query
            num_results: Number of results to return
            time_range: Time filter (e.g., "d1", "w1", "m1")
            site: Restrict to a specific site

        Returns:
            List of search results
        """
        pass

    @abstractmethod
    async def search_and_visit(
        self,
        query: str,
        max_visits: int = 3,
        browser: Optional[BrowserProvider] = None,
    ) -> List[ScrapedContent]:
        """
        Search and visit the top results.

        Args:
            query: Search query
            max_visits: Maximum number of pages to visit
            browser: Browser provider for visiting pages

        Returns:
            List of scraped content from visited pages
        """
        pass

    @abstractmethod
    async def news_search(
        self,
        query: str,
        num_results: int = 10,
        days: int = 7,
    ) -> List[SearchResult]:
        """
        Perform a news search.

        Args:
            query: Search query
            num_results: Number of results to return
            days: Number of days to search back

        Returns:
            List of search results
        """
        pass


# ============================================================================
# Export all interfaces
# ============================================================================


__all__ = [
    # Enums
    "BrowserType",
    "PageLoadState",
    # Data classes
    "SearchResult",
    "ScrapedContent",
    "NavigationResult",
    "Screenshot",
    "BrowserState",
    # Interfaces
    "BrowserProvider",
    "SearchEngine",
]