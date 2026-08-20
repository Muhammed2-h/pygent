import pytest
import json
from tools.browser import (
    browser_sessions, 
    browser_scan, 
    browser_execute_js, 
    browser_cdp, 
    browser_screenshot,
    setup_browser_tools
)
from browser.session import Session, BrowserSessionManager
from browser.driver import BrowserDriver
from browser.transport import BrowserTransport
from browser.cdp import CDPClient
from browser.observer import BrowserObserver
from datetime import datetime

# Provide dummy implementations for testing
class DummySessionManager(BrowserSessionManager):
    pass

class DummyDriver:
    async def execute_js(self, session_id, tab_id, script):
        return {"result": 42, "navigated": False, "new_tabs": []}
    
    async def browser_screenshot(self, session_id, tab_id):
        return {"base64": "abc", "mime_type": "image/png", "width": 800, "height": 600}

class DummyObserver:
    async def scan(self, session_id, tab_id, options):
        return {"html": "<div>Test</div>", "interactive_elements": [], "tabs": [], "element_references": {}}

class DummyCDP:
    async def send_command(self, session_id, tab_id, method, params, timeout=None):
        return {"value": 100}

@pytest.fixture(autouse=True)
def setup_tools():
    session_manager = DummySessionManager()
    driver = DummyDriver()
    observer = DummyObserver()
    cdp = DummyCDP()
    setup_browser_tools(driver, session_manager, observer, cdp)
    return session_manager, driver, observer, cdp

def test_browser_sessions(setup_tools):
    session_manager = setup_tools[0]
    s = Session(session_id="sess1", tab_id="tab1", url="http://example.com", title="Example", active=True, connected=True, last_seen=datetime.now(), connection_type="ws")
    session_manager.set_session(s)
    
    res = browser_sessions()
    assert "Example" in res
    assert "sess1" in res
    assert "http://example.com" in res
    
    session_manager.remove_session("sess1")

@pytest.mark.asyncio
async def test_browser_scan():
    res_str = await browser_scan("sess1", 123)
    res = json.loads(res_str)
    assert res["html"] == "<div>Test</div>"

@pytest.mark.asyncio
async def test_browser_execute_js():
    res_str = await browser_execute_js("sess1", 123, "return 42;")
    res = json.loads(res_str)
    assert res["result"] == 42

@pytest.mark.asyncio
async def test_browser_cdp():
    res_str = await browser_cdp("sess1", 123, "Runtime.evaluate", {"expression": "100"})
    res = json.loads(res_str)
    assert res["value"] == 100

@pytest.mark.asyncio
async def test_browser_screenshot():
    res_str = await browser_screenshot("sess1", 123)
    res = json.loads(res_str)
    assert res["base64"] == "abc"
    assert res["width"] == 800
