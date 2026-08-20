import pytest
import asyncio
from browser.cdp import CDPClient
from browser.models import ExtensionRequest, ExtensionResponse

class DummyTransport:
    def __init__(self):
        self.sent_requests = []
        self.call_count = 0
        
    async def send_command(self, session_id, req):
        self.sent_requests.append(req)
        self.call_count += 1
        return f"msg{self.call_count}"
    
    async def receive_result(self, session_id, timeout=None):
        req = self.sent_requests[-1]
        if req.cmd == "debugger_send_command":
            return ExtensionResponse(id=f"msg{self.call_count}", ok=True, data={"result": "ok"})
        return ExtensionResponse(id=f"msg{self.call_count}", ok=False, error="Unknown cmd")
        
    def acknowledge(self, session_id, msg_id):
        pass

@pytest.mark.asyncio
async def test_cdp_client_methods():
    transport = DummyTransport()
    client = CDPClient(transport=transport)
    
    # test runtime_evaluate
    res = await client.runtime_evaluate("sess1", 123, "1 + 1")
    assert res == {"result": "ok"}
    assert transport.sent_requests[-1].cmd == "debugger_send_command"
    assert transport.sent_requests[-1].tabId == 123
    assert transport.sent_requests[-1].payload["method"] == "Runtime.evaluate"
    assert transport.sent_requests[-1].payload["commandParams"]["expression"] == "1 + 1"
    
    # test page_navigate
    res = await client.page_navigate("sess1", 123, "http://example.com")
    assert transport.sent_requests[-1].payload["method"] == "Page.navigate"
    assert transport.sent_requests[-1].payload["commandParams"]["url"] == "http://example.com"
    
    # test page_capture_screenshot
    await client.page_capture_screenshot("sess1", 123, format="jpeg", quality=80)
    assert transport.sent_requests[-1].payload["method"] == "Page.captureScreenshot"
    assert transport.sent_requests[-1].payload["commandParams"]["format"] == "jpeg"
    assert transport.sent_requests[-1].payload["commandParams"]["quality"] == 80
    
    # test page_bring_to_front
    await client.page_bring_to_front("sess1", 123)
    assert transport.sent_requests[-1].payload["method"] == "Page.bringToFront"
    
    # test dom_get_document
    await client.dom_get_document("sess1", 123)
    assert transport.sent_requests[-1].payload["method"] == "DOM.getDocument"
    
    # test dom_query_selector
    await client.dom_query_selector("sess1", 123, 456, "div")
    assert transport.sent_requests[-1].payload["method"] == "DOM.querySelector"
    assert transport.sent_requests[-1].payload["commandParams"]["nodeId"] == 456
    
    # test dom_get_box_model
    await client.dom_get_box_model("sess1", 123, backend_node_id=789)
    assert transport.sent_requests[-1].payload["method"] == "DOM.getBoxModel"
    assert transport.sent_requests[-1].payload["commandParams"]["backendNodeId"] == 789
    
    # test input_dispatch_mouse_event
    await client.input_dispatch_mouse_event("sess1", 123, "mousePressed", 10, 20, button="left")
    assert transport.sent_requests[-1].payload["method"] == "Input.dispatchMouseEvent"
    assert transport.sent_requests[-1].payload["commandParams"]["type"] == "mousePressed"
    assert transport.sent_requests[-1].payload["commandParams"]["button"] == "left"
    
    # test input_dispatch_key_event
    await client.input_dispatch_key_event("sess1", 123, "keyDown", key="Enter")
    assert transport.sent_requests[-1].payload["method"] == "Input.dispatchKeyEvent"
    assert transport.sent_requests[-1].payload["commandParams"]["key"] == "Enter"
