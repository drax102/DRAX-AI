"""
browser_tools.py — Agentic browser automation and navigation controller using Playwright & system browser fallback.
Supports opening URLs, web searches, clicking, typing, scrolling, hovering, tab management, reading pages, and extracting content.
"""

import threading
import urllib.parse
import webbrowser
from bs4 import BeautifulSoup
import requests

from backend.agent.tool_registry import register_tool
from backend.core.logger import get_logger
from backend.plugins.open_website import open_website as plugin_open_website

logger = get_logger(__name__)

_playwright_driver = None
_playwright_browser = None
_playwright_page = None
_browser_lock = threading.Lock()


def _ensure_browser():
    """Lazy initialize Playwright browser instance if available."""
    global _playwright_driver, _playwright_browser, _playwright_page
    with _browser_lock:
        if _playwright_page is not None:
            return _playwright_page
        try:
            from playwright.sync_api import sync_playwright
            _playwright_driver = sync_playwright().start()
            _playwright_browser = _playwright_driver.chromium.launch(headless=False)
            _playwright_page = _playwright_browser.new_page()
            return _playwright_page
        except Exception as e:
            logger.warning(f"Playwright browser initialization not available ({e}) — using system browser fallback.")
            return None


@register_tool(
    name="open_url",
    description="Open a specific URL or domain in the default web browser.",
    parameters={"url": {"type": "string", "description": "Website address or domain (e.g. https://github.com, lpu.in)"}},
    risk_level="low",
    category="browser",
)
def open_url(url: str) -> str:
    return plugin_open_website(url)


@register_tool(
    name="search_web",
    description="Search Google, YouTube, GitHub, Reddit, or Wikipedia for a query.",
    parameters={
        "query": {"type": "string", "description": "Search term"},
        "engine": {"type": "string", "description": "Search engine: google, youtube, github, reddit, wikipedia", "default": "google"},
    },
    risk_level="low",
    category="browser",
)
def search_web(query: str, engine: str = "google") -> str:
    engines = {
        "google": "https://www.google.com/search?q=",
        "youtube": "https://www.youtube.com/results?search_query=",
        "github": "https://github.com/search?q=",
        "reddit": "https://www.reddit.com/search/?q=",
        "wikipedia": "https://en.wikipedia.org/wiki/Special:Search?search=",
    }
    base_url = engines.get(engine.lower(), engines["google"])
    full_url = base_url + urllib.parse.quote(query)
    webbrowser.open(full_url)
    return f"Searching {engine.capitalize()} for '{query}'."


@register_tool(
    name="browser_navigate",
    description="Navigate the automated browser agent to a URL.",
    parameters={"url": {"type": "string", "description": "Target website URL"}},
    risk_level="low",
    category="browser",
)
def browser_navigate(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    page = _ensure_browser()
    if page:
        try:
            page.goto(url, timeout=20000)
            return f"Navigated browser to {url}. Title: {page.title()}"
        except Exception as e:
            logger.error(f"Browser navigation error: {e}")

    webbrowser.open(url)
    return f"Opened {url} in default browser."


@register_tool(
    name="browser_click",
    description="Click an element, link, or button on the active browser page by text or CSS selector.",
    parameters={"target": {"type": "string", "description": "Button/link text or CSS selector"}},
    risk_level="medium",
    category="browser",
)
def browser_click(target: str) -> str:
    page = _ensure_browser()
    if not page:
        return "Browser automation session is not currently active."
    try:
        try:
            page.get_by_text(target, exact=False).first.click(timeout=5000)
            return f"Clicked element with text '{target}'."
        except Exception:
            page.locator(target).first.click(timeout=5000)
            return f"Clicked element matching selector '{target}'."
    except Exception as e:
        return f"Could not click '{target}': {str(e)}"


@register_tool(
    name="browser_type",
    description="Type text into an input box or search field on the active webpage.",
    parameters={
        "target": {"type": "string", "description": "Field placeholder, label, or selector"},
        "text": {"type": "string", "description": "Text to type into the field"},
    },
    risk_level="medium",
    category="browser",
)
def browser_type(target: str, text: str) -> str:
    page = _ensure_browser()
    if not page:
        return "Browser automation session is not currently active."
    try:
        try:
            page.get_by_placeholder(target).fill(text, timeout=5000)
        except Exception:
            page.locator(target).first.fill(text, timeout=5000)
        return f"Typed '{text}' into {target}."
    except Exception as e:
        return f"Could not type into '{target}': {str(e)}"


@register_tool(
    name="browser_scroll",
    description="Scroll the active browser page up or down.",
    parameters={"direction": {"type": "string", "description": "'down' or 'up'", "default": "down"}},
    risk_level="low",
    category="browser",
)
def browser_scroll(direction: str = "down") -> str:
    page = _ensure_browser()
    if not page:
        return "Browser automation session is not currently active."
    try:
        pixels = 600 if direction.lower() == "down" else -600
        page.evaluate(f"window.scrollBy(0, {pixels})")
        return f"Scrolled page {direction}."
    except Exception as e:
        return f"Scroll failed: {str(e)}"


@register_tool(
    name="browser_hover",
    description="Hover mouse over an element or menu on the active webpage.",
    parameters={"target": {"type": "string", "description": "Element text or CSS selector"}},
    risk_level="low",
    category="browser",
)
def browser_hover(target: str) -> str:
    page = _ensure_browser()
    if not page:
        return "Browser automation session is not active."
    try:
        try:
            page.get_by_text(target, exact=False).first.hover(timeout=5000)
        except Exception:
            page.locator(target).first.hover(timeout=5000)
        return f"Hovered over '{target}'."
    except Exception as e:
        return f"Hover failed on '{target}': {str(e)}"


@register_tool(
    name="browser_back",
    description="Navigate back to the previous webpage in browser history.",
    parameters={},
    risk_level="low",
    category="browser",
)
def browser_back() -> str:
    page = _ensure_browser()
    if not page:
        return "Browser automation session is not active."
    try:
        page.go_back(timeout=5000)
        return f"Navigated back to {page.url}."
    except Exception as e:
        return f"Go back failed: {str(e)}"


@register_tool(
    name="browser_forward",
    description="Navigate forward to the next webpage in browser history.",
    parameters={},
    risk_level="low",
    category="browser",
)
def browser_forward() -> str:
    page = _ensure_browser()
    if not page:
        return "Browser automation session is not active."
    try:
        page.go_forward(timeout=5000)
        return f"Navigated forward to {page.url}."
    except Exception as e:
        return f"Go forward failed: {str(e)}"


@register_tool(
    name="browser_open_tab",
    description="Open a new browser tab with an optional URL.",
    parameters={"url": {"type": "string", "description": "URL to open in new tab", "default": "https://google.com"}},
    risk_level="low",
    category="browser",
)
def browser_open_tab(url: str = "https://google.com") -> str:
    global _playwright_browser, _playwright_page
    _ensure_browser()
    if _playwright_browser:
        try:
            _playwright_page = _playwright_browser.new_page()
            _playwright_page.goto(url)
            return f"Opened new tab: {url}."
        except Exception as e:
            return f"Failed to open new tab: {str(e)}"
    webbrowser.open_new_tab(url)
    return f"Opened new tab with {url} in default browser."


@register_tool(
    name="browser_close_tab",
    description="Close the currently active browser tab.",
    parameters={},
    risk_level="medium",
    category="browser",
)
def browser_close_tab() -> str:
    global _playwright_page
    if _playwright_page:
        try:
            _playwright_page.close()
            _playwright_page = None
            return "Closed active browser tab."
        except Exception as e:
            return f"Failed to close tab: {str(e)}"
    return "No automated tab is currently open."


@register_tool(
    name="browser_extract",
    description="Extract text content or list elements from a webpage matching a CSS or XPath selector.",
    parameters={"selector": {"type": "string", "description": "CSS selector to extract (e.g. 'h2', '.job-title', '#price')"}},
    risk_level="low",
    category="browser",
)
def browser_extract(selector: str) -> str:
    page = _ensure_browser()
    if not page:
        return "Browser automation session is not active."
    try:
        elements = page.locator(selector).all_text_contents()
        if not elements:
            return f"No elements matched selector '{selector}'."
        cleaned = [e.strip() for e in elements if e.strip()][:8]
        return f"Extracted items matching '{selector}':\n- " + "\n- ".join(cleaned)
    except Exception as e:
        return f"Extraction failed for selector '{selector}': {str(e)}"


@register_tool(
    name="browser_read_page",
    description="Read and summarize the text content of the active webpage or a given URL.",
    parameters={"url": {"type": "string", "description": "Optional URL to fetch if browser is inactive", "default": ""}},
    risk_level="low",
    category="browser",
)
def browser_read_page(url: str = "") -> str:
    page = _ensure_browser()
    if page and not url:
        try:
            content = page.inner_text("body")
            lines = [l.strip() for l in content.split("\n") if len(l.strip()) > 30]
            summary = "\n".join(lines[:10])
            return f"Page content ({page.title()}):\n{summary[:800]}"
        except Exception as e:
            logger.warning(f"Failed to read from page: {e}")

    if url:
        if not url.startswith("http"):
            url = f"https://{url}"
        try:
            resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(resp.text, "html.parser")
            paragraphs = [p.get_text().strip() for p in soup.find_all(["p", "h1", "h2", "h3"]) if len(p.get_text().strip()) > 30]
            return f"Content from {url}:\n" + "\n".join(paragraphs[:6])[:700]
        except Exception as e:
            return f"Could not read webpage at {url}: {e}"

    return "No active webpage to read."
