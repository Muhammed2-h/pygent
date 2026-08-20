import json
from typing import Any, Dict, Optional, Union
from browser.driver import BrowserDriver
from browser.transport import BrowserTransport
from browser.session import BrowserSessionManager
from browser.cdp import CDPClient
from browser.observer import BrowserObserver
from .registry import tool

_driver: Optional[BrowserDriver] = None
_session_manager: Optional[BrowserSessionManager] = None
_observer: Optional[BrowserObserver] = None
_cdp: Optional[CDPClient] = None

def setup_browser_tools(
    driver: BrowserDriver,
    session_manager: BrowserSessionManager,
    observer: BrowserObserver,
    cdp: CDPClient
):
    """Initializes the global dependencies for the browser tools."""
    global _driver, _session_manager, _observer, _cdp
    _driver = driver
    _session_manager = session_manager
    _observer = observer
    _cdp = cdp


@tool(
    name="browser_sessions",
    description="List all active browser sessions and tabs. Use this first to find the target `session_id` and `tab_id` before executing other browser commands.",
    category="browser"
)
def browser_sessions() -> str:
    """Returns a JSON string of all active sessions and tabs."""
    if not _session_manager:
        return "Browser tools not initialized."
    sessions = _session_manager.list_sessions()
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
    description="Scan the DOM of the specified browser tab to extract interactive elements and text. Use this to understand the page structure, find elements to interact with, and get references for subsequent actions.",
    category="browser"
)
async def browser_scan(session_id: str, tab_id: Union[int, str], max_chars: int = 0, tabs_only: bool = False, text_only: bool = False) -> str:
    """
    Scans the browser tab DOM.
    Returns JSON containing 'html', 'interactive_elements', 'tabs', and 'element_references'.
    """
    if not _observer:
        return "Browser tools not initialized."
    options = {
        "max_chars": max_chars,
        "tabs_only": tabs_only,
        "text_only": text_only
    }
    # Ensure tab_id is an int before passing to driver if the underlying driver expects int, 
    # but the reviewer asked to change type annotation to match session.py. We will coerce it 
    # if necessary, or just pass it as is since driver.execute_js etc. might accept both.
    if isinstance(tab_id, str) and tab_id.isdigit():
        tab_id = int(tab_id)
        
    result = await _observer.scan(session_id, tab_id, options=options)
    return json.dumps(result, indent=2)

@tool(
    name="browser_execute_js",
    description="Execute custom JavaScript in the specified browser tab. Use this to interact with the DOM, trigger events, extract custom data, or modify page state. Note: this runs in the context of the page, so variables and functions are isolated per page load.",
    category="browser"
)
async def browser_execute_js(session_id: str, tab_id: Union[int, str], script: str) -> str:
    """
    Executes a script in the specified tab. 
    Returns JSON containing the execution 'result', a 'navigated' boolean, and any 'new_tabs' detected.
    """
    if not _driver:
        return "Browser tools not initialized."
    if isinstance(tab_id, str) and tab_id.isdigit():
        tab_id = int(tab_id)
    try:
        result = await _driver.execute_js(session_id, tab_id, script)
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error executing JS: {e}"

@tool(
    name="browser_cdp",
    description="Send a raw Chrome DevTools Protocol (CDP) command to the browser tab. Use this for low-level browser automation (e.g., simulating complex input events, overriding network responses, manipulating the box model, etc.). Requires familiarity with CDP methods and parameters.",
    category="browser"
)
async def browser_cdp(session_id: str, tab_id: Union[int, str], method: str, params: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None) -> str:
    """
    Executes a CDP command via the browser's debugger API.
    """
    if not _cdp:
        return "Browser tools not initialized."
    if isinstance(tab_id, str) and tab_id.isdigit():
        tab_id = int(tab_id)
    try:
        result = await _cdp.send_command(session_id, tab_id, method, params, timeout=timeout)
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error executing CDP command: {e}"

@tool(
    name="browser_screenshot",
    description="Capture a screenshot of the current page in the specified browser tab. Use this when visual context is needed to verify UI state, or to confirm if a specific action (like a click or navigation) succeeded visually.",
    category="browser"
)
async def browser_screenshot(session_id: str, tab_id: Union[int, str]) -> str:
    """
    Captures a screenshot using CDP. Returns JSON with 'base64', 'mime_type', 'width', and 'height'.
    """
    if not _driver:
        return "Browser tools not initialized."
    if isinstance(tab_id, str) and tab_id.isdigit():
        tab_id = int(tab_id)
    try:
        result = await _driver.browser_screenshot(session_id, tab_id)
        return json.dumps(result)
    except Exception as e:
        return f"Error taking screenshot: {e}"
