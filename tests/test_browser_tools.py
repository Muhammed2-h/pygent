import pytest
import json
from tools.browser import browser_sessions, browser_scan, browser_execute_js, browser_cdp, browser_screenshot
from tools.browser import session_manager, driver, observer, cdp
from browser.session import Session
from datetime import datetime

@pytest.mark.asyncio
async def test_browser_sessions():
    # Setup mock session
    s = Session(session_id="sess1", tab_id="tab1", url="http://example.com", title="Example", active=True, connected=True, last_seen=datetime.now(), connection_type="ws")
    session_manager.set_session(s)
    
    res = browser_sessions()
    assert "Example" in res
    assert "sess1" in res
    assert "http://example.com" in res
    
    session_manager.remove_session("sess1")

@pytest.mark.asyncio
async def test_browser_scan(monkeypatch):
    async def mock_scan(session_id, tab_id, options):
        return {"html": "<div>Test</div>", "interactive_elements": [], "tabs": [], "element_references": {}}
    monkeypatch.setattr(observer, "scan", mock_scan)
    
    res_str = await browser_scan("sess1", 123)
    res = json.loads(res_str)
    assert res["html"] == "<div>Test</div>"

@pytest.mark.asyncio
async def test_browser_execute_js(monkeypatch):
    async def mock_execute(session_id, tab_id, script):
        return {"result": 42, "navigated": False, "new_tabs": []}
    monkeypatch.setattr(driver, "execute_js", mock_execute)
    
    res_str = await browser_execute_js("sess1", 123, "return 42;")
    res = json.loads(res_str)
    assert res["result"] == 42

@pytest.mark.asyncio
async def test_browser_cdp(monkeypatch):
    async def mock_send(session_id, tab_id, method, params, timeout=None):
        return {"value": 100}
    monkeypatch.setattr(cdp, "send_command", mock_send)
    
    res_str = await browser_cdp("sess1", 123, "Runtime.evaluate", {"expression": "100"})
    res = json.loads(res_str)
    assert res["value"] == 100

@pytest.mark.asyncio
async def test_browser_screenshot(monkeypatch):
    async def mock_screenshot(session_id, tab_id):
        return {"base64": "abc", "mime_type": "image/png", "width": 800, "height": 600}
    monkeypatch.setattr(driver, "browser_screenshot", mock_screenshot)
    
    res_str = await browser_screenshot("sess1", 123)
    res = json.loads(res_str)
    assert res["base64"] == "abc"
    assert res["width"] == 800
