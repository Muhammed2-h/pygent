"""
Chrome DevTools Protocol (CDP) Module.

Provides a structured interface for interacting with CDP endpoints.
"""

import asyncio
from typing import Any, Dict, Optional
from browser.transport import BrowserTransport
from browser.models import ExtensionRequest

class CDPClient:
    """Client for executing Chrome DevTools Protocol commands."""
    
    def __init__(self, transport: Optional[BrowserTransport] = None, default_timeout: float = 60.0):
        """
        Initialize the CDP client.
        
        Args:
            transport: The transport layer to send commands through.
            default_timeout: Default timeout in seconds for receiving command responses.
        """
        self.transport = transport
        self.default_timeout = default_timeout

    async def send_command(self, session_id: str, tab_id: int, method: str, params: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None) -> Any:
        """
        Send a raw CDP command and wait for its response.
        
        Args:
            session_id: The browser session ID.
            tab_id: The ID of the tab to execute the command in.
            method: The CDP method to execute (e.g. 'Runtime.evaluate').
            params: Optional parameters for the CDP method.
            timeout: Optional timeout for the command (overrides default_timeout).
            
        Returns:
            The raw response data from the CDP command.
        """
        if not self.transport:
            raise RuntimeError("Transport not configured")
        
        req = ExtensionRequest(
            cmd="debugger_send_command",
            tabId=tab_id,
            payload={
                "method": method,
                "commandParams": params or {}
            }
        )
        msg_id = await self.transport.send_command(session_id, req)
        
        effective_timeout = timeout if timeout is not None else self.default_timeout
        resp = await self.transport.receive_result(session_id, msg_id, timeout=effective_timeout)
        self.transport.acknowledge(session_id, msg_id)
        if not resp.ok:
            raise RuntimeError(f"CDP command '{method}' failed: {resp.error}")
        return resp.data

    async def runtime_evaluate(self, session_id: str, tab_id: int, expression: str, return_by_value: bool = True, timeout: Optional[float] = None) -> Any:
        """
        Evaluate JavaScript expression in the tab.
        
        Args:
            session_id: The browser session ID.
            tab_id: The ID of the tab.
            expression: The JS expression to evaluate.
            return_by_value: Whether to return the actual value (default) or an object reference.
            timeout: Optional command timeout.
        """
        return await self.send_command(session_id, tab_id, "Runtime.evaluate", {
            "expression": expression,
            "returnByValue": return_by_value
        }, timeout=timeout)

    async def page_navigate(self, session_id: str, tab_id: int, url: str, timeout: Optional[float] = None) -> Any:
        """
        Navigate the page to a given URL.
        
        Args:
            session_id: The browser session ID.
            tab_id: The ID of the tab.
            url: The destination URL.
            timeout: Optional command timeout.
        """
        return await self.send_command(session_id, tab_id, "Page.navigate", {
            "url": url
        }, timeout=timeout)

    async def page_capture_screenshot(self, session_id: str, tab_id: int, image_format: str = "png", quality: int = 100, timeout: Optional[float] = None) -> Any:
        """
        Capture a screenshot of the page.
        
        Args:
            session_id: The browser session ID.
            tab_id: The ID of the tab.
            image_format: 'png', 'jpeg', or 'webp' (default 'png').
            quality: Image compression quality for jpeg/webp (0-100).
            timeout: Optional command timeout.
        """
        params = {"format": image_format}
        if image_format in ("jpeg", "webp"):
            params["quality"] = quality
        return await self.send_command(session_id, tab_id, "Page.captureScreenshot", params, timeout=timeout)

    async def page_bring_to_front(self, session_id: str, tab_id: int, timeout: Optional[float] = None) -> Any:
        """
        Bring the page to the front (make it the active tab).
        
        Args:
            session_id: The browser session ID.
            tab_id: The ID of the tab.
            timeout: Optional command timeout.
        """
        return await self.send_command(session_id, tab_id, "Page.bringToFront", timeout=timeout)

    async def dom_get_document(self, session_id: str, tab_id: int, depth: int = -1, pierce: bool = False, timeout: Optional[float] = None) -> Any:
        """
        Returns the root DOM node.
        
        Args:
            session_id: The browser session ID.
            tab_id: The ID of the tab.
            depth: How many levels to fetch. -1 means entire subtree.
            pierce: Whether to traverse into shadow DOMs.
            timeout: Optional command timeout.
        """
        return await self.send_command(session_id, tab_id, "DOM.getDocument", {
            "depth": depth,
            "pierce": pierce
        }, timeout=timeout)

    async def dom_query_selector(self, session_id: str, tab_id: int, node_id: int, selector: str, timeout: Optional[float] = None) -> Any:
        """
        Executes querySelector on a given node.
        
        Args:
            session_id: The browser session ID.
            tab_id: The ID of the tab.
            node_id: The parent node ID to query inside.
            selector: The CSS selector.
            timeout: Optional command timeout.
        """
        return await self.send_command(session_id, tab_id, "DOM.querySelector", {
            "nodeId": node_id,
            "selector": selector
        }, timeout=timeout)

    async def dom_get_box_model(self, session_id: str, tab_id: int, node_id: Optional[int] = None, backend_node_id: Optional[int] = None, object_id: Optional[str] = None, timeout: Optional[float] = None) -> Any:
        """
        Returns boxes (bounding rects) for the given node.
        
        Args:
            session_id: The browser session ID.
            tab_id: The ID of the tab.
            node_id: Optional DOM node ID.
            backend_node_id: Optional backend node ID.
            object_id: Optional remote object ID.
            timeout: Optional command timeout.
        """
        params = {}
        if node_id is not None:
            params["nodeId"] = node_id
        if backend_node_id is not None:
            params["backendNodeId"] = backend_node_id
        if object_id is not None:
            params["objectId"] = object_id
        return await self.send_command(session_id, tab_id, "DOM.getBoxModel", params, timeout=timeout)

    async def input_dispatch_mouse_event(self, session_id: str, tab_id: int, event_type: str, x: float, y: float, timeout: Optional[float] = None, **kwargs) -> Any:
        """
        Dispatches a mouse event.
        
        Args:
            session_id: The browser session ID.
            tab_id: The ID of the tab.
            event_type: 'mousePressed', 'mouseReleased', 'mouseMoved', 'mouseWheel'.
            x: X coordinate relative to viewport.
            y: Y coordinate relative to viewport.
            timeout: Optional command timeout.
            kwargs: Additional event attributes like 'button' (e.g. 'left', 'middle', 'right', 'none').
        """
        params = {
            "type": event_type,
            "x": x,
            "y": y
        }
        params.update(kwargs)
        return await self.send_command(session_id, tab_id, "Input.dispatchMouseEvent", params, timeout=timeout)

    async def input_dispatch_key_event(self, session_id: str, tab_id: int, event_type: str, timeout: Optional[float] = None, **kwargs) -> Any:
        """
        Dispatches a key event.
        
        Args:
            session_id: The browser session ID.
            tab_id: The ID of the tab.
            event_type: 'keyDown', 'keyUp', 'rawKeyDown', 'char'.
            timeout: Optional command timeout.
            kwargs: Additional event attributes like 'key', 'code', 'windowsVirtualKeyCode'.
        """
        params = {
            "type": event_type
        }
        params.update(kwargs)
        return await self.send_command(session_id, tab_id, "Input.dispatchKeyEvent", params, timeout=timeout)