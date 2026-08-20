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
    
    def __init__(self, transport: Optional[BrowserTransport] = None):
        self.transport = transport

    async def send_command(self, session_id: str, tab_id: int, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Send a raw CDP command."""
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
        
        while True:
            resp = await self.transport.receive_result(session_id, timeout=60.0)
            if resp.id == msg_id:
                self.transport.acknowledge(session_id, msg_id)
                if not resp.ok:
                    raise RuntimeError(f"CDP command '{method}' failed: {resp.error}")
                return resp.data

    async def runtime_evaluate(self, session_id: str, tab_id: int, expression: str, return_by_value: bool = True) -> Any:
        """Evaluate JavaScript expression."""
        return await self.send_command(session_id, tab_id, "Runtime.evaluate", {
            "expression": expression,
            "returnByValue": return_by_value
        })

    async def page_navigate(self, session_id: str, tab_id: int, url: str) -> Any:
        """Navigate the page to a URL."""
        return await self.send_command(session_id, tab_id, "Page.navigate", {
            "url": url
        })

    async def page_capture_screenshot(self, session_id: str, tab_id: int, format: str = "png", quality: int = 100) -> Any:
        """Capture a screenshot of the page."""
        params = {"format": format}
        if format in ("jpeg", "webp"):
            params["quality"] = quality
        return await self.send_command(session_id, tab_id, "Page.captureScreenshot", params)

    async def page_bring_to_front(self, session_id: str, tab_id: int) -> Any:
        """Bring the page to front."""
        return await self.send_command(session_id, tab_id, "Page.bringToFront")

    async def dom_get_document(self, session_id: str, tab_id: int, depth: int = -1, pierce: bool = False) -> Any:
        """Returns the root DOM node."""
        return await self.send_command(session_id, tab_id, "DOM.getDocument", {
            "depth": depth,
            "pierce": pierce
        })

    async def dom_query_selector(self, session_id: str, tab_id: int, node_id: int, selector: str) -> Any:
        """Executes querySelector on a given node."""
        return await self.send_command(session_id, tab_id, "DOM.querySelector", {
            "nodeId": node_id,
            "selector": selector
        })

    async def dom_get_box_model(self, session_id: str, tab_id: int, node_id: Optional[int] = None, backend_node_id: Optional[int] = None, object_id: Optional[str] = None) -> Any:
        """Returns boxes for the given node."""
        params = {}
        if node_id is not None:
            params["nodeId"] = node_id
        if backend_node_id is not None:
            params["backendNodeId"] = backend_node_id
        if object_id is not None:
            params["objectId"] = object_id
        return await self.send_command(session_id, tab_id, "DOM.getBoxModel", params)

    async def input_dispatch_mouse_event(self, session_id: str, tab_id: int, type: str, x: float, y: float, **kwargs) -> Any:
        """Dispatches a mouse event."""
        params = {
            "type": type,
            "x": x,
            "y": y
        }
        params.update(kwargs)
        return await self.send_command(session_id, tab_id, "Input.dispatchMouseEvent", params)

    async def input_dispatch_key_event(self, session_id: str, tab_id: int, type: str, **kwargs) -> Any:
        """Dispatches a key event."""
        params = {
            "type": type
        }
        params.update(kwargs)
        return await self.send_command(session_id, tab_id, "Input.dispatchKeyEvent", params)
