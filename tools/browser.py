import json
from typing import Any, Dict, Optional
from browser.driver import BrowserDriver
from browser.transport import BrowserTransport
from browser.session import BrowserSessionManager
from browser.cdp import CDPClient
from browser.observer import BrowserObserver
from .registry import tool

transport = BrowserTransport()
session_manager = BrowserSessionManager()
driver = BrowserDriver(transport=transport, session_manager=session_manager)
observer = BrowserObserver(driver=driver)
cdp = CDPClient(transport=transport)

@tool(
    name="browser_sessions",
    description="List all active browser sessions and tabs.",
    category="browser"
)
def browser_sessions() -> str:
    """Returns a JSON string of all active sessions and tabs."""
    sessions = session_manager.list_sessions()
    if not sessions:
        return "No active browser sessions."
    return json.dumps([
        {
            "session_id": s.session_id,
            "tab_id": s.tab_id,
            "url": s.url,
            "title": s.title,
            "active": s.active
        } for s in sessions
    ], indent=2)

@tool(
    name="browser_scan",
    description="Scan the DOM of the specified browser tab to extract interactive elements and text.",
    category="browser"
)
async def browser_scan(session_id: str, tab_id: int, max_chars: int = 0, tabs_only: bool = False, text_only: bool = False) -> str:
    """
    Scans the browser tab DOM.
    Returns JSON containing 'html', 'interactive_elements', 'tabs', and 'element_references'.
    """
    options = {
        "max_chars": max_chars,
        "tabs_only": tabs_only,
        "text_only": text_only
    }
    result = await observer.scan(session_id, tab_id, options=options)
    return json.dumps(result, indent=2)

@tool(
    name="browser_execute_js",
    description="Execute JavaScript in the specified browser tab.",
    category="browser"
)
async def browser_execute_js(session_id: str, tab_id: int, script: str) -> str:
    """
    Executes a script in the specified tab. 
    Returns JSON containing the execution 'result', a 'navigated' boolean, and any 'new_tabs' detected.
    """
    try:
        result = await driver.execute_js(session_id, tab_id, script)
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error executing JS: {e}"

@tool(
    name="browser_cdp",
    description="Send a raw Chrome DevTools Protocol (CDP) command to the browser tab.",
    category="browser"
)
async def browser_cdp(session_id: str, tab_id: int, method: str, params: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None) -> str:
    """
    Executes a CDP command via the browser's debugger API.
    """
    try:
        result = await cdp.send_command(session_id, tab_id, method, params, timeout=timeout)
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error executing CDP command: {e}"

@tool(
    name="browser_screenshot",
    description="Capture a screenshot of the current page in the specified browser tab.",
    category="browser"
)
async def browser_screenshot(session_id: str, tab_id: int) -> str:
    """
    Captures a screenshot using CDP. Returns JSON with 'base64', 'mime_type', 'width', and 'height'.
    """
    try:
        result = await driver.browser_screenshot(session_id, tab_id)
        return json.dumps(result)
    except Exception as e:
        return f"Error taking screenshot: {e}"
