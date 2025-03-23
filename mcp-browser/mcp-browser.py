#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "mcp[cli]",
#    "playwright" 
# ]
# ///
# This script connects to an existing Chrome-compatible browser instance
# Launch Chrome-compatible with: brave --remote-debugging-port=9222
from typing import Optional, Union, Any, List
import asyncio
import base64
import sys
from mcp.server import FastMCP

# Create an MCP server for web browsing
mcp = FastMCP("Web Browser")

# Global browser and page management
_browser = None
_browser_context = None
_current_page = None
_playwright_instance = None
_cdp_url = "http://localhost:9222"  # CDP URL for Chrome-compatible browser

# Dynamic import of Playwright to avoid early import errors
def _import_playwright():
    from playwright.async_api import async_playwright
    return async_playwright

async def _ensure_browser():
    """Connect to existing Chrome-compatible browser instance over CDP"""
    global _browser, _browser_context, _playwright_instance, _cdp_url
    
    if _browser is None:
        try:
            playwright_module = _import_playwright()
            _playwright_instance = await playwright_module().start()
            
            # Connect to existing Chrome-compatible browser instance over CDP
            print(f"Connecting to Chrome-compatible browser at {_cdp_url}", file=sys.stderr)
            _browser = await _playwright_instance.chromium.connect_over_cdp(_cdp_url)
            
            # Get the default browser context
            # Note: when connecting to an existing browser, we use the default context
            _browser_context = _browser.contexts[0] if _browser.contexts else await _browser.new_context(
                ignore_https_errors=True,  # Ignore SSL certificate errors
            )
            
            print("Successfully connected to Chrome-compatible browser", file=sys.stderr)
        except Exception as e:
            print(f"Error connecting to Chrome-compatible browser at {_cdp_url}: {e}", file=sys.stderr)
            print("Make sure Chrome is running with the --remote-debugging-port=9222 flag", file=sys.stderr)
            raise
            
    return _browser, _browser_context

async def _get_active_page():
    """Get the currently active page in the browser"""
    global _browser
    
    _, _ = await _ensure_browser()
    
    try:
        # Get all pages across all contexts
        all_pages = []
        for context in _browser.contexts:
            all_pages.extend(context.pages)
        
        if not all_pages:
            return None
            
        # Try multiple methods to determine the active page
        
        # Method 1: Use CDP to determine page visibility and focus
        for page in all_pages:
            # Check both visibility state and focus
            is_visible = await page.evaluate("""() => {
                return document.visibilityState === 'visible';
            }""")
            is_focused = await page.evaluate("document.hasFocus()")
            
            # Also check the URL to filter out extension pages
            url = page.url
            is_extension = url.startswith("chrome-extension://") or url.startswith("brave-extension://")
            
            # Consider a page active if it's visible, has focus, and is not an extension
            if is_visible and is_focused and not is_extension:
                print(f"Found active page: {url}", file=sys.stderr)
                return page
        
        # Method 2: Check for recent interaction (more reliable in some cases)
        try:
            # This requires additional CDP capabilities
            for page in all_pages:
                # Skip extension pages
                if page.url.startswith("chrome-extension://") or page.url.startswith("brave-extension://"):
                    continue
                    
                # Use the page's title as a basic check
                title = await page.title()
                if title:  # Non-empty title might indicate a regular page
                    url = page.url
                    # Skip about:blank and similar utility pages
                    if not url.startswith("about:") and not url.startswith("chrome:"):
                        print(f"Using best guess active page: {url}", file=sys.stderr)
                        return page
        except Exception as e:
            print(f"Error in method 2: {e}", file=sys.stderr)
                
        # Fallback: if no page has focus, return the most recently created one
        # Filter out extension pages first
        regular_pages = [p for p in all_pages if not (p.url.startswith("chrome-extension://") or
                                                      p.url.startswith("brave-extension://") or
                                                      p.url.startswith("about:") or
                                                      p.url.startswith("chrome:"))]
        
        if regular_pages:
            print(f"Fallback to most recent regular page: {regular_pages[-1].url}", file=sys.stderr)
            return regular_pages[-1]
        
        # Last resort: just return the most recent page even if it's an extension
        print(f"Last resort fallback: {all_pages[-1].url}", file=sys.stderr)
        return all_pages[-1]
    except Exception as e:
        print(f"Error getting active page: {e}", file=sys.stderr)
        return None

async def _get_page_to_use() -> Any:
    """Helper function to get the current page to operate on.
    
    First tries the page we navigated to via browse_to.
    If that's not available, tries to get the active tab.
    
    Returns:
        The page object to use for browser operations
        
    Raises:
        ValueError: If no page is available
    """
    # First try with the page we navigated to via browse_to
    page_to_use = _current_page
    
    # If we don't have a current page, try to get the active tab
    if not page_to_use:
        page_to_use = await _get_active_page()
        
    if not page_to_use:
        raise ValueError("No page is currently loaded or active in the browser.")
        
    return page_to_use

async def _close_current_page():
    """Close the current page if it exists"""
    global _current_page
    if _current_page:
        try:
            await _current_page.close()
        except Exception:
            pass
        _current_page = None

async def _safe_cleanup():
    """Safely clean up browser resources"""
    global _browser, _current_page, _browser_context, _playwright_instance
    
    try:
        if _current_page:
            try:
                await _current_page.close()
            except Exception:
                pass
        
        if _browser_context:
            try:
                await _browser_context.close()
            except Exception:
                pass
        
        if _browser:
            try:
                await _browser.close()
            except Exception:
                pass
        
        if _playwright_instance:
            try:
                await _playwright_instance.stop()
            except Exception:
                pass
    except Exception as e:
        # Log the error, but don't re-raise
        print(f"Error during cleanup: {e}", file=sys.stderr)
    finally:
        # Reset global variables
        _browser = None
        _browser_context = None
        _current_page = None
        _playwright_instance = None

@mcp.tool()
async def browse_to(url: str, context: Optional[Any] = None) -> str:
    """
    Navigate to a specific URL and return the page's HTML content.
    
    Args:
        url: The full URL to navigate to
        context: Optional context object for logging (ignored)
    
    Returns:
        The full HTML content of the page
    """
    global _current_page, _browser, _browser_context
    
    # Ensure browser is launched with SSL validation disabled
    _, browser_context = await _ensure_browser()
    
    # Close any existing page
    await _close_current_page()
    
    # Optional logging, but do nothing with context
    print(f"Navigating to {url}", file=sys.stderr)
    
    try:
        # Create a new page and navigate
        _current_page = await browser_context.new_page()
        
        # Additional options to handle various SSL/security issues
        await _current_page.goto(url, 
            wait_until='networkidle',
            timeout=30000,  # 30 seconds timeout
        )
        
        # Get full page content including dynamically loaded JavaScript
        page_content = await _current_page.content()
        
        # Optional: extract additional metadata
        try:
            title = await _current_page.title()
            print(f"Page title: {title}", file=sys.stderr)
        except Exception:
            pass
        
        return page_content
    
    except Exception as e:
        print(f"Error navigating to {url}: {e}", file=sys.stderr)
        raise

@mcp.tool()
async def get_page_info(context: Optional[Any] = None) -> dict:
    """
    Get information about the current active page including URL, title, and other metadata.
    
    Args:
        context: Optional context object for logging (ignored)
        
    Returns:
        Dictionary containing page information including:
        - url: The current page URL
        - title: The current page title
        - is_secure: Whether the page is using HTTPS
        - favicon: Favicon URL if available
    """
    page_to_use = await _get_page_to_use()
    
    try:
        url = page_to_use.url
        title = await page_to_use.title()
        
        # Additional metadata
        is_secure = url.startswith("https://")
        
        # Get favicon using JavaScript (may not work on all pages)
        try:
            favicon = await page_to_use.evaluate("""
                () => {
                    const link = document.querySelector("link[rel='shortcut icon']") || 
                              document.querySelector("link[rel='icon']");
                    return link ? link.href : null;
                }
            """)
        except Exception:
            favicon = None
            
        return {
            "url": url,
            "title": title,
            "is_secure": is_secure,
            "favicon": favicon
        }
    except Exception as e:
        print(f"Error getting page info: {e}", file=sys.stderr)
        raise ValueError(f"Error getting page info: {e}")

# Maintain backward compatibility with individual functions
@mcp.tool()
async def get_current_url(context: Optional[Any] = None) -> str:
    """
    Get the URL of the current active page.
    
    Args:
        context: Optional context object for logging (ignored)
        
    Returns:
        The current page URL
    """
    page_info = await get_page_info(context)
    return page_info["url"]

@mcp.tool()
async def get_page_title(context: Optional[Any] = None) -> str:
    """
    Get the title of the current active page.
    
    Args:
        context: Optional context object for logging (ignored)
        
    Returns:
        The current page title
    """
    page_info = await get_page_info(context)
    return page_info["title"]

@mcp.tool()
async def get_page_content(
    content_type: str = "html", 
    selector: Optional[str] = None,
    context: Optional[Any] = None
) -> str:
    """
    Get content from the current page in various formats.
    
    Args:
        content_type: Type of content to return ("html", "text", or "links")
        selector: Optional CSS selector to limit content to a specific element
        context: Optional context object for logging (ignored)
    
    Returns:
        The requested content from the page
    """
    page_to_use = await _get_page_to_use()
    
    try:
        # Get the content based on the requested type
        if content_type == "html":
            if selector:
                # Get HTML of a specific element
                element = await page_to_use.query_selector(selector)
                if not element:
                    raise ValueError(f"No element found with selector: {selector}")
                content = await page_to_use.evaluate(f"""(element) => element.outerHTML""", element)
            else:
                # Get full page HTML
                content = await page_to_use.content()
                
        elif content_type == "text":
            if selector:
                # Get text of specific elements
                elements = await page_to_use.query_selector_all(selector)
                content = "\n".join([await el.inner_text() for el in elements])
            else:
                # Get all visible text from the page
                content = await page_to_use.inner_text('body')
                
        elif content_type == "links":
            # Use JavaScript to extract all links
            if selector:
                content = await page_to_use.evaluate(f"""
                    () => {{
                        const elements = document.querySelectorAll('{selector}');
                        return Array.from(elements)
                            .filter(el => el.tagName === 'A')
                            .map(link => link.href);
                    }}
                """)
            else:
                content = await page_to_use.evaluate("""
                    () => {{
                        const links = document.querySelectorAll('a');
                        return Array.from(links).map(link => link.href);
                    }}
                """)
        else:
            raise ValueError(f"Invalid content_type: {content_type}. Valid options are 'html', 'text', or 'links'")
            
        return content
    
    except Exception as e:
        print(f"Error getting page content: {e}", file=sys.stderr)
        raise ValueError(f"Error getting page content: {e}")

# Keep original function for backward compatibility
@mcp.tool()
async def get_active_tab_content(context: Optional[Any] = None) -> str:
    """
    Get the HTML content of the currently active tab in the browser.
    This doesn't change the _current_page used by other functions.
    
    Args:
        context: Optional context object for logging (ignored)
    
    Returns:
        The full HTML content of the active tab
    """
    # First, list all available pages for debugging
    _, _ = await _ensure_browser()
    all_pages = []
    
    try:
        for context in _browser.contexts:
            all_pages.extend(context.pages)
        
        print(f"All available pages ({len(all_pages)}):", file=sys.stderr)
        for i, page in enumerate(all_pages):
            url = page.url
            title = await page.title() if not url.startswith("chrome-extension://") else "Extension"
            print(f"  [{i}] {url} - {title}", file=sys.stderr)
    except Exception as e:
        print(f"Error listing pages: {e}", file=sys.stderr)
    
    # Try to get the active page directly
    active_page = await _get_active_page()
    
    if not active_page:
        raise ValueError("No active page found in the browser")
    
    try:
        # Log detailed information about the active page
        url = active_page.url
        title = await active_page.title()
        print(f"Selected active tab: {url}", file=sys.stderr)
        print(f"Active tab title: {title}", file=sys.stderr)
        
        # Get the content of the active page
        page_content = await active_page.content()
        
        return page_content
    
    except Exception as e:
        print(f"Error getting active tab content: {e}", file=sys.stderr)
        raise ValueError(f"Error getting active tab content: {e}")

@mcp.tool()
async def extract_text_content(
    selector: Optional[str] = None, 
    context: Optional[Any] = None
) -> str:
    """
    Extract text content from the current page, optionally using a CSS selector.

    Args:
        selector: Optional CSS selector to target specific elements
        context: Optional context object for logging (ignored)
    
    Returns:
        Extracted text content
    """
    text_content = await get_page_content(content_type="text", selector=selector, context=context)
    print(f"Extracted text content" + (f" from selector: {selector}" if selector else ""), file=sys.stderr)
    return text_content

@mcp.tool()
async def interact_with_page(
    action: str,
    selector: str,
    value: Optional[str] = None,
    context: Optional[Any] = None
) -> str:
    """
    Interact with elements on the current page in various ways.
    
    Args:
        action: The type of interaction ('click', 'type', 'select', 'hover', 'focus', 'press')
        selector: CSS selector for the element to interact with
        value: Optional value for actions that require it (text for typing, key for pressing, etc.)
        context: Optional context object for logging (ignored)
    
    Returns:
        Confirmation message or error details
    """
    page_to_use = await _get_page_to_use()
    
    try:
        # First, get the element
        element = await page_to_use.query_selector(selector)
        if not element:
            raise ValueError(f"No element found with selector: {selector}")
        
        # Perform the requested action
        action = action.lower()
        
        if action == "click":
            await element.click()
            message = f"Clicked element: {selector}"
            
        elif action == "type" or action == "fill":
            if not value:
                raise ValueError("The 'value' parameter must be provided for 'type' action")
            await element.fill(value)
            message = f"Typed text into element: {selector}"
            
        elif action == "select":
            if not value:
                raise ValueError("The 'value' parameter must be provided for 'select' action")
            await element.select_option(value)
            message = f"Selected option in element: {selector}"
            
        elif action == "hover":
            await element.hover()
            message = f"Hovered over element: {selector}"
            
        elif action == "focus":
            await element.focus()
            message = f"Focused on element: {selector}"
            
        elif action == "press":
            if not value:
                raise ValueError("The 'value' parameter must be provided for 'press' action")
            await element.press(value)
            message = f"Pressed {value} on element: {selector}"
            
        else:
            raise ValueError(f"Invalid action: {action}. Valid actions are 'click', 'type', 'select', 'hover', 'focus', 'press'")
        
        print(message, file=sys.stderr)
        return f"Successfully performed {action} on {selector}"
    
    except Exception as e:
        print(f"Error performing {action}: {e}", file=sys.stderr)
        raise ValueError(f"Error performing {action}: {e}")

# Keep original functions for backward compatibility
@mcp.tool()
async def click_element(
    selector: str, 
    context: Optional[Any] = None
) -> str:
    """
    Click an element on the current page.
    
    Args:
        selector: CSS selector for the element to click
        context: Optional context object for logging (ignored)
    
    Returns:
        Confirmation message or error details
    """
    return await interact_with_page("click", selector, context=context)

@mcp.tool()
async def get_page_screenshots(
    full_page: bool = False, 
    selector: Optional[str] = None,
    context: Optional[Any] = None
) -> str:
    """
    Capture screenshot of the current page.
    
    Args:
        full_page: Whether to capture the entire page or just the viewport
        selector: Optional CSS selector to screenshot a specific element
        context: Optional context object for logging (ignored)
    
    Returns:
        Base64 encoded screenshot image
    """
    page_to_use = await _get_page_to_use()
    
    try:
        if selector:
            element = await page_to_use.query_selector(selector)
            if not element:
                raise ValueError(f"No element found with selector: {selector}")
            screenshot_bytes = await element.screenshot()
        else:
            screenshot_bytes = await page_to_use.screenshot(full_page=full_page)
        
        # Convert to base64 for easy transmission
        screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
        
        print(f"Screenshot captured: {'full page' if full_page else 'viewport'}", file=sys.stderr)
        
        return screenshot_base64
    
    except Exception as e:
        print(f"Error capturing screenshot: {e}", file=sys.stderr)
        raise ValueError(f"Error capturing screenshot: {e}")

@mcp.tool()
async def get_page_links(selector: Optional[str] = None, context: Optional[Any] = None) -> list[str]:
    """
    Extract all links from the current page, optionally filtered by a CSS selector.
    
    Args:
        selector: Optional CSS selector to limit link extraction to specific elements
        context: Optional context object for logging (ignored)
    
    Returns:
        List of links found on the page
    """
    links = await get_page_content(content_type="links", selector=selector, context=context)
    print(f"Extracted {len(links)} links from the page", file=sys.stderr)
    return links

@mcp.tool()
async def input_text(
        selector: str, 
        text: str, 
        context: Optional[Any] = None
        ) -> str:
    """
    Input text into a specific element on the page.
    
    Args:
        selector: CSS selector for the input element
        text: Text to input
        context: Optional context object for logging (ignored)
    
    Returns:
        Confirmation message
    """
    return await interact_with_page("type", selector, value=text, context=context)

@mcp.tool()
async def evaluate_javascript(
        script: str,
        args: Optional[List[Any]] = None,
        context: Optional[Any] = None
        ) -> Any:
    """
    Execute arbitrary JavaScript in the context of the current page and return the result.

    Args:
        script: JavaScript code to execute. Must be wrapped in a function or IIFE that explicitly returns a value.
               For example: "(() => { return document.title; })()" or "function() { return document.title; }()"
               Note: Console.log statements are not captured in the return value.
        args: Optional list of arguments to pass to the script
        context: Optional context object for logging (ignored)

    Returns:
        Result of the JavaScript execution (the explicitly returned value from your script)
    """
    page_to_use = await _get_page_to_use()

    try:
        # Execute the JavaScript in the page context
        result = await page_to_use.evaluate(script, args or [])
        return result
    except Exception as e:
        print(f"Error executing JavaScript: {e}", file=sys.stderr)
        raise ValueError(f"Error executing JavaScript: {e}")

@mcp.tool()
async def force_browse_to_active_tab(context: Optional[Any] = None) -> str:
    """
    Attempt to forcefully detect and browse to the currently active tab.
    This uses browser debugging protocol directly to list tabs and find the active one.
    
    Args:
        context: Optional context object for logging (ignored)
    
    Returns:
        Information about the detected active tab
    """
    global _current_page, _browser, _browser_context
    
    # First connect to the browser if not already connected
    await _ensure_browser()
    
    try:
        # Use browser debugging protocol to list tabs
        # This JavaScript execution happens in the default page context
        # but accesses CDP to list all tabs
        if not _browser or not _browser.contexts or not _browser.contexts[0].pages:
            raise ValueError("Browser not properly connected")
            
        # Get a page to execute our detection script in
        page = _browser.contexts[0].pages[0]
        
        # Execute tab detection script
        tabs_info = await page.evaluate("""
        async () => {
            try {
                // Try to directly access Chrome DevTools Protocol
                // This requires proper permissions with CDP
                const response = await fetch('http://localhost:9222/json');
                const tabs = await response.json();
                
                // Find tabs that look like real browser tabs (not extensions/devtools)
                const realTabs = tabs.filter(tab => {
                    return tab.type === 'page' && 
                           !tab.url.startsWith('chrome-extension://') &&
                           !tab.url.startsWith('brave-extension://') &&
                           !tab.url.startsWith('chrome-devtools://') &&
                           !tab.url.startsWith('about:') &&
                           !tab.url.includes('devtools');
                });
                
                return { 
                    success: true,
                    message: 'Retrieved tabs via CDP',
                    allTabs: tabs,
                    realTabs: realTabs
                };
            } catch (error) {
                return { 
                    success: false, 
                    error: error.toString(),
                    message: 'Failed to retrieve tabs via CDP'
                };
            }
        }
        """)
        
        print(f"Tab detection results: {tabs_info}", file=sys.stderr)
        
        # If we found tabs, try to navigate to what looks like the active one
        if tabs_info.get('success') and tabs_info.get('realTabs'):
            real_tabs = tabs_info.get('realTabs')
            
            # For now, just pick the first real tab (you might need more logic here)
            target_tab = real_tabs[0]
            
            # Now create a new page navigated to this URL
            _current_page = await _browser_context.new_page()
            
            # Navigate to the same URL as the active tab
            await _current_page.goto(target_tab['url'], 
                wait_until='networkidle',
                timeout=30000,
            )
            
            return f"Successfully detected and navigated to tab: {target_tab['url']}"
        else:
            return f"Failed to detect active tab: {tabs_info.get('message', 'Unknown error')}"
            
    except Exception as e:
        print(f"Error in force_browse_to_active_tab: {e}", file=sys.stderr)
        return f"Error detecting active tab: {e}"

def main():
    try:
        mcp.run()
    except Exception as e:
        print(f"Error running MCP server: {e}", file=sys.stderr)
    finally:
        # Use a separate event loop to ensure cleanup
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_safe_cleanup())
            loop.close()
        except Exception as cleanup_error:
            print(f"Cleanup error: {cleanup_error}", file=sys.stderr)

if __name__ == "__main__":
    main()
