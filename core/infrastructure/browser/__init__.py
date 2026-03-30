"""
Browser automation infrastructure module using Playwright.

Provides automated web browser capabilities for:
    - Web searching (Google, Bing)
    - Page navigation and content extraction
    - DOM element interaction
    - Cookie and session management
    - Screenshot capture
    - JavaScript execution

Features:
    - Full async/await support
    - Multiple browser types (Chromium, Firefox, WebKit)
    - Dynamic page load handling
    - Automatic error recovery
    - Headless and headed modes

Usage:
    from core.infrastructure.browser import PlaywrightBrowserProvider, BrowserType
    
    provider = PlaywrightBrowserProvider(
        browser_type=BrowserType.CHROMIUM,
        headless=True
    )
    await provider.initialize()
    
    # Search the web
    results = await provider.search("competitive intelligence", num_results=10)
    
    # Scrape content
    content = await provider.get_scraped_content("https://example.com")
    
    await provider.close()
"""

from core.infrastructure.browser.playwright_provider import PlaywrightBrowserProvider

__all__ = [
    "PlaywrightBrowserProvider",
]
