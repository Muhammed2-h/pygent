import pytest
import asyncio
from browser.driver import BrowserDriver
from browser.transport import BrowserTransport
from browser.models import ExtensionResponse, ExtensionRequest

@pytest.mark.asyncio
async def test_browser_execute_js():
    class DummyTransport:
        def __init__(self):
            self.call_count = 0
            
        async def send_command(self, session_id, req):
            self.req = req
            self.call_count += 1
            return f"msg{self.call_count}"
        
        async def receive_result(self, session_id, timeout=None):
            if self.req.cmd == "enumerate_tabs":
                return ExtensionResponse(id=f"msg{self.call_count}", ok=True, data=[{"id": 123, "url": "http://a.com"}])
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
