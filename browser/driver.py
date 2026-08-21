"""
Browser Driver Module.

Provides the main driver interface for interacting with the browser subsystem.
"""

from typing import Any, Optional
from browser.transport import BrowserTransport
from browser.models import ExtensionRequest
from browser.cdp import CDPClient
import asyncio

class BrowserDriver:
    """Main driver for the browser engine."""
    def __init__(self, transport: Optional[BrowserTransport] = None, session_manager=None):
        self.transport = transport
        self.session_manager = session_manager

    async def enumerate_tabs(self, session_id: str) -> list:
        req = ExtensionRequest(cmd="enumerate_tabs", payload={})
        msg_id = await self.transport.send_command(session_id, req)
        resp = await self.transport.receive_result(session_id, msg_id, timeout=60.0)
        self.transport.acknowledge(session_id, msg_id)
        if not resp.ok:
            raise RuntimeError(f"Failed to enumerate tabs: {resp.error}")
        return resp.data

    async def execute_js(self, session_id: str, tab_id: int, script: str) -> dict:
        """
        Execute JavaScript in the target tab.
        Returns a dict with 'result', 'navigated', and 'new_tabs'.
        """
        if not self.transport:
            raise RuntimeError("Transport not configured")
            
        try:
            tabs_before = await self.enumerate_tabs(session_id)
        except Exception:
            tabs_before = []
            
        active_tab_before = next((t for t in tabs_before if t.get("id") == tab_id), None)
        url_before = active_tab_before.get("url") if active_tab_before else None
            
        req = ExtensionRequest(
            cmd="execute",
            payload={"tabId": tab_id, "script": script}
        )
        msg_id = await self.transport.send_command(session_id, req)
        
        result_data = None
        exec_error = None
        
        try:
            resp = await self.transport.receive_result(session_id, msg_id, timeout=60.0)
            self.transport.acknowledge(session_id, msg_id)
            if not resp.ok:
                exec_error = resp.error
            else:
                result_data = resp.data
                if isinstance(result_data, dict) and result_data.get("__pygent_error"):
                    exec_error = f"JS Error: {result_data.get('message')}\nStack: {result_data.get('stack')}"
        except asyncio.TimeoutError:
            exec_error = "Timeout waiting for JavaScript execution"
        except Exception as e:
            exec_error = str(e)
            
        try:
            tabs_after = await self.enumerate_tabs(session_id)
        except Exception:
            tabs_after = []
            
        active_tab_after = next((t for t in tabs_after if t.get("id") == tab_id), None)
        url_after = active_tab_after.get("url") if active_tab_after else None
        
        navigated = False
        if url_before and url_after and url_before != url_after:
            navigated = True
        elif active_tab_before and not active_tab_after:
            navigated = True
            
        new_tabs = [t for t in tabs_after if t.get("id") not in [tb.get("id") for tb in tabs_before]]
        
        if exec_error and "Execution context was destroyed" in exec_error:
            navigated = True
            exec_error = None
            
        if exec_error and "Cannot find context with specified id" in exec_error:
            navigated = True
            exec_error = None
            
        if exec_error:
            raise RuntimeError(exec_error)
            
        return {
            "result": result_data,
            "navigated": navigated,
            "new_tabs": new_tabs
        }

    async def browser_screenshot(self, session_id: str, tab_id: int) -> dict:
        """
        Capture a screenshot of the current page.
        Returns a dictionary with base64, mime_type, width, and height.
        """
        if not self.transport:
            raise RuntimeError("Transport not configured")
            
        cdp = CDPClient(self.transport)
        
        # Get viewport dimensions
        eval_resp = await cdp.runtime_evaluate(
            session_id,
            tab_id,
            "({width: window.innerWidth, height: window.innerHeight})"
        )
        
        width = 800
        height = 600
        
        if isinstance(eval_resp, dict) and "result" in eval_resp:
            result_val = eval_resp["result"].get("value", {})
            if isinstance(result_val, dict):
                width = result_val.get("width", width)
                height = result_val.get("height", height)
                
        # Capture screenshot
        screen_resp = await cdp.page_capture_screenshot(session_id, tab_id, image_format="png")
        
        base64_data = ""
        if isinstance(screen_resp, dict):
            base64_data = screen_resp.get("data", "")
            
        return {
            "base64": base64_data,
            "mime_type": "image/png",
            "width": width,
            "height": height
        }
