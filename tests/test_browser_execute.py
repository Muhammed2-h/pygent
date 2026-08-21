
import pytest

from browser.driver import BrowserDriver
from browser.models import ExtensionResponse


@pytest.mark.asyncio
async def test_browser_execute_js_happy_path():
    class DummyTransport:
        def __init__(self):
            self.call_count = 0
            
        async def send_command(self, session_id, req):
            self.req = req
            self.call_count += 1
            return f"msg{self.call_count}"
        
        async def receive_result(self, session_id, msg_id, timeout=None):
            if self.req.cmd == "enumerate_tabs":
                return ExtensionResponse(id=f"msg{self.call_count}", ok=True, data=[{"id": 123, "url": "http://example.com"}])
            elif self.req.cmd == "execute":
                return ExtensionResponse(id=f"msg{self.call_count}", ok=True, data={"result": "test_output"})
            return ExtensionResponse(id=f"msg{self.call_count}", ok=False, error="Unknown")
            
        def acknowledge(self, session_id, msg_id):
            pass

    transport = DummyTransport()
    driver = BrowserDriver(transport=transport)
    
    res = await driver.execute_js("sess1", 123, "return 42;")
    assert res["result"] == {"result": "test_output"}
    assert res["navigated"] is False
    assert res["new_tabs"] == []

@pytest.mark.asyncio
async def test_browser_execute_js_navigation_detection():
    class DummyTransport:
        def __init__(self):
            self.call_count = 0
            
        async def send_command(self, session_id, req):
            self.req = req
            self.call_count += 1
            return f"msg{self.call_count}"
        
        async def receive_result(self, session_id, msg_id, timeout=None):
            if self.req.cmd == "enumerate_tabs":
                if self.call_count == 1:
                    return ExtensionResponse(id=f"msg{self.call_count}", ok=True, data=[{"id": 123, "url": "http://a.com"}])
                else:
                    return ExtensionResponse(id=f"msg{self.call_count}", ok=True, data=[{"id": 123, "url": "http://b.com"}, {"id": 124, "url": "http://new.com"}])
            elif self.req.cmd == "execute":
                return ExtensionResponse(id=f"msg{self.call_count}", ok=True, data={"result": None})
            return ExtensionResponse(id=f"msg{self.call_count}", ok=False, error="Unknown")
            
        def acknowledge(self, session_id, msg_id):
            pass

    transport = DummyTransport()
    driver = BrowserDriver(transport=transport)
    
    res = await driver.execute_js("sess1", 123, "window.location.href = 'http://b.com'; window.open('http://new.com');")
    assert res["navigated"] is True
    assert len(res["new_tabs"]) == 1
    assert res["new_tabs"][0]["id"] == 124

@pytest.mark.asyncio
async def test_browser_execute_js_error_extraction():
    class DummyTransport:
        def __init__(self):
            self.call_count = 0
            
        async def send_command(self, session_id, req):
            self.req = req
            self.call_count += 1
            return f"msg{self.call_count}"
        
        async def receive_result(self, session_id, msg_id, timeout=None):
            if self.req.cmd == "enumerate_tabs":
                return ExtensionResponse(id=f"msg{self.call_count}", ok=True, data=[{"id": 123, "url": "http://example.com"}])
            elif self.req.cmd == "execute":
                return ExtensionResponse(id=f"msg{self.call_count}", ok=True, data={"__pygent_error": True, "message": "SyntaxError", "stack": "..."})
            return ExtensionResponse(id=f"msg{self.call_count}", ok=False, error="Unknown")
            
        def acknowledge(self, session_id, msg_id):
            pass

    transport = DummyTransport()
    driver = BrowserDriver(transport=transport)
    
    with pytest.raises(RuntimeError, match="JS Error: SyntaxError"):
        await driver.execute_js("sess1", 123, "return foo bar;")
