import pytest
import asyncio
from browser.observer import BrowserObserver

@pytest.mark.asyncio
async def test_observer_scan(browser_env, local_server):
    transport = browser_env["transport"]
    driver = browser_env["driver"]
    session_id = browser_env["session_id"]
    
    tabs = await driver.enumerate_tabs(session_id)
    tab_id = tabs[0]["id"]
    
    # load test page
    await driver.execute_js(session_id, tab_id, f"window.location.href = '{local_server}/index.html';")
    for _ in range(20):
        tabs = await driver.enumerate_tabs(session_id)
        if any("index.html" in t["url"] for t in tabs):
            break
        await asyncio.sleep(0.1)
    
    observer = BrowserObserver(transport)
    scan_res = await observer.scan(session_id, tab_id)
    
    assert "elements" in scan_res
    assert isinstance(scan_res["elements"], list)
    assert any(el.get("tagName", "").lower() == "button" for el in scan_res["elements"])
